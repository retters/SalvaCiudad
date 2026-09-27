#include "render/model.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <format>
#include <memory>

#include <cgltf.h>
#include <stb_image.h>

namespace sc::render {

namespace lim = model_limits;

namespace {

struct DataDeleter {
    void operator()(cgltf_data* d) const { cgltf_free(d); }
};
struct ImageDeleter {
    void operator()(stbi_uc* p) const { stbi_image_free(p); }
};

math::Mat4 to_mat4(const cgltf_float m[16]) {
    math::Mat4 r;
    std::memcpy(&r.m[0][0], m, sizeof(float) * 16);  // glTF is column-major too.
    return r;
}

// Decodes the embedded image of a texture into RGBA8.
bool load_texture(const cgltf_texture& tex, ModelTexture& out, std::string& error) {
    const cgltf_image* image = tex.image;
    if (image == nullptr || image->buffer_view == nullptr || image->uri != nullptr) {
        error = "textures must be embedded in the .glb";
        return false;
    }
    const cgltf_buffer_view* view = image->buffer_view;
    const std::uint8_t* bytes = cgltf_buffer_view_data(view);
    if (bytes == nullptr || view->size == 0 || view->size > lim::kMaxFileBytes) {
        error = "invalid texture data";
        return false;
    }
    const int len = static_cast<int>(view->size);
    int w = 0;
    int h = 0;
    int comp = 0;
    if (stbi_info_from_memory(bytes, len, &w, &h, &comp) == 0 || w <= 0 || h <= 0 ||
        w > lim::kMaxTextureSize || h > lim::kMaxTextureSize) {
        error = "texture is not a PNG or JPEG of at most 4096 x 4096";
        return false;
    }
    std::unique_ptr<stbi_uc, ImageDeleter> pixels(stbi_load_from_memory(bytes, len, &w, &h, &comp, 4));
    if (!pixels) {
        error = "texture could not be decoded";
        return false;
    }
    out.width = w;
    out.height = h;
    out.rgba.assign(pixels.get(), pixels.get() + static_cast<std::size_t>(w) * static_cast<std::size_t>(h) * 4);
    return true;
}

class Builder {
public:
    Builder(const cgltf_data& data, ModelData& model) : data_(data), model_(model) {}

    bool build(std::string& error) {
        if (!load_materials(error)) {
            return false;
        }
        const cgltf_scene* scene = data_.scene != nullptr ? data_.scene : (data_.scenes_count > 0 ? data_.scenes : nullptr);
        if (scene == nullptr) {
            error = "the file has no scene";
            return false;
        }
        for (cgltf_size i = 0; i < scene->nodes_count; ++i) {
            if (!add_node(*scene->nodes[i], 0, error)) {
                return false;
            }
        }
        if (model_.primitives.empty()) {
            error = "the scene has no triangles";
            return false;
        }
        return true;
    }

private:
    bool load_materials(std::string& error) {
        if (data_.textures_count > lim::kMaxTextures) {
            error = "too many textures";
            return false;
        }
        for (cgltf_size i = 0; i < data_.textures_count; ++i) {
            ModelTexture tex;
            if (!load_texture(data_.textures[i], tex, error)) {
                return false;
            }
            model_.textures.push_back(std::move(tex));
        }
        for (cgltf_size i = 0; i < data_.materials_count; ++i) {
            model_.materials.push_back(convert_material(data_.materials[i]));
        }
        // Primitives without a material use a white default at the end.
        default_material_ = static_cast<std::uint32_t>(model_.materials.size());
        model_.materials.push_back(ModelMaterial{});
        return true;
    }

    ModelMaterial convert_material(const cgltf_material& m) const {
        ModelMaterial out;
        if (m.has_pbr_metallic_roughness) {
            for (int c = 0; c < 4; ++c) {
                out.base_color[c] = std::clamp(m.pbr_metallic_roughness.base_color_factor[c], 0.0f, 1.0f);
            }
            if (const cgltf_texture* t = m.pbr_metallic_roughness.base_color_texture.texture) {
                out.texture = static_cast<int>(t - data_.textures);
            }
        }
        return out;
    }

    bool add_node(const cgltf_node& node, int depth, std::string& error) {
        if (depth > 32) {
            error = "node hierarchy too deep";
            return false;
        }
        if (node.mesh != nullptr) {
            cgltf_float world[16];
            cgltf_node_transform_world(&node, world);
            const math::Mat4 m = to_mat4(world);
            if (!add_mesh(*node.mesh, m, error)) {
                return false;
            }
        }
        for (cgltf_size i = 0; i < node.children_count; ++i) {
            if (!add_node(*node.children[i], depth + 1, error)) {
                return false;
            }
        }
        return true;
    }

    bool add_mesh(const cgltf_mesh& mesh, const math::Mat4& world, std::string& error) {
        // Normals use the inverse transpose, so non-uniform scale stays correct.
        const math::Mat4 inv = math::inverse(world);
        math::Mat4 normal_m;
        for (int c = 0; c < 4; ++c) {
            for (int r = 0; r < 4; ++r) {
                normal_m.m[c][r] = inv.m[r][c];
            }
        }
        for (cgltf_size p = 0; p < mesh.primitives_count; ++p) {
            const cgltf_primitive& prim = mesh.primitives[p];
            if (prim.type != cgltf_primitive_type_triangles) {
                continue;  // Points and lines are not drawn.
            }
            if (model_.primitives.size() >= lim::kMaxPrimitives) {
                error = "too many primitives";
                return false;
            }
            if (!add_primitive(prim, world, normal_m, error)) {
                return false;
            }
        }
        return true;
    }

    bool add_primitive(const cgltf_primitive& prim, const math::Mat4& world, const math::Mat4& normal_m,
                       std::string& error) {
        const cgltf_accessor* pos = nullptr;
        const cgltf_accessor* nrm = nullptr;
        const cgltf_accessor* uv = nullptr;
        for (cgltf_size a = 0; a < prim.attributes_count; ++a) {
            const cgltf_attribute& attr = prim.attributes[a];
            if (attr.type == cgltf_attribute_type_position && attr.index == 0) pos = attr.data;
            if (attr.type == cgltf_attribute_type_normal && attr.index == 0) nrm = attr.data;
            if (attr.type == cgltf_attribute_type_texcoord && attr.index == 0) uv = attr.data;
        }
        if (pos == nullptr || pos->type != cgltf_type_vec3 || pos->count == 0) {
            error = "a primitive has no positions";
            return false;
        }
        const cgltf_size count = pos->count;
        if ((nrm != nullptr && (nrm->type != cgltf_type_vec3 || nrm->count != count)) ||
            (uv != nullptr && (uv->type != cgltf_type_vec2 || uv->count != count))) {
            error = "a primitive has attributes of mismatched size or type";
            return false;
        }
        if (model_.vertices.size() + count > lim::kMaxVertices) {
            error = "too many vertices";
            return false;
        }

        const auto base = static_cast<std::uint32_t>(model_.vertices.size());
        for (cgltf_size i = 0; i < count; ++i) {
            float p[3] = {0, 0, 0};
            float n[3] = {0, 1, 0};
            float t[2] = {0, 0};
            if (!cgltf_accessor_read_float(pos, i, p, 3) || (nrm != nullptr && !cgltf_accessor_read_float(nrm, i, n, 3)) ||
                (uv != nullptr && !cgltf_accessor_read_float(uv, i, t, 2))) {
                error = "unreadable vertex data";
                return false;
            }
            const math::Vec3 wp = world.transform_point({p[0], p[1], p[2]});
            const math::Vec3 wn = math::normalize(normal_m.transform_vector({n[0], n[1], n[2]}));
            if (!std::isfinite(wp.x) || !std::isfinite(wp.y) || !std::isfinite(wp.z)) {
                error = "vertex position is not a finite number";
                return false;
            }
            model_.vertices.push_back({wp.x, wp.y, wp.z, wn.x, wn.y, wn.z, t[0], t[1]});
        }

        ModelPrimitive out;
        out.first_index = static_cast<std::uint32_t>(model_.indices.size());
        if (prim.indices != nullptr) {
            const cgltf_size index_count = prim.indices->count;
            if (index_count % 3 != 0 || model_.indices.size() + index_count > lim::kMaxIndices) {
                error = "invalid or too many indices";
                return false;
            }
            for (cgltf_size i = 0; i < index_count; ++i) {
                const cgltf_size idx = cgltf_accessor_read_index(prim.indices, i);
                if (idx >= count) {
                    error = "index out of range";
                    return false;
                }
                model_.indices.push_back(base + static_cast<std::uint32_t>(idx));
            }
            out.index_count = static_cast<std::uint32_t>(index_count);
        } else {
            if (count % 3 != 0 || model_.indices.size() + count > lim::kMaxIndices) {
                error = "invalid or too many vertices for unindexed triangles";
                return false;
            }
            for (cgltf_size i = 0; i < count; ++i) {
                model_.indices.push_back(base + static_cast<std::uint32_t>(i));
            }
            out.index_count = static_cast<std::uint32_t>(count);
        }
        if (nrm == nullptr) {
            compute_flat_normals(out);
        }
        out.material = prim.material != nullptr ? static_cast<std::uint32_t>(prim.material - data_.materials)
                                                : default_material_;
        model_.primitives.push_back(out);
        return true;
    }

    // Without normals in the file, each triangle gets its face normal.
    void compute_flat_normals(const ModelPrimitive& prim) {
        for (std::uint32_t i = 0; i + 2 < prim.index_count; i += 3) {
            ModelVertex& a = model_.vertices[model_.indices[prim.first_index + i]];
            ModelVertex& b = model_.vertices[model_.indices[prim.first_index + i + 1]];
            ModelVertex& c = model_.vertices[model_.indices[prim.first_index + i + 2]];
            const math::Vec3 n = math::normalize(math::cross(math::Vec3{b.px - a.px, b.py - a.py, b.pz - a.pz},
                                                             math::Vec3{c.px - a.px, c.py - a.py, c.pz - a.pz}));
            for (ModelVertex* v : {&a, &b, &c}) {
                v->nx = n.x;
                v->ny = n.y;
                v->nz = n.z;
            }
        }
    }

    const cgltf_data& data_;
    ModelData& model_;
    std::uint32_t default_material_ = 0;
};

void compute_bounds(ModelData& model) {
    math::Vec3 lo{1e30f, 1e30f, 1e30f};
    math::Vec3 hi{-1e30f, -1e30f, -1e30f};
    float r2 = 0.0f;
    for (const ModelVertex& v : model.vertices) {
        lo = {std::min(lo.x, v.px), std::min(lo.y, v.py), std::min(lo.z, v.pz)};
        hi = {std::max(hi.x, v.px), std::max(hi.y, v.py), std::max(hi.z, v.pz)};
        r2 = std::max(r2, v.px * v.px + v.py * v.py + v.pz * v.pz);
    }
    model.bounds_min = lo;
    model.bounds_max = hi;
    model.radius = std::sqrt(r2);
}

}  // namespace

ModelLoadResult load_glb(std::span<const std::uint8_t> file) {
    ModelLoadResult result;
    if (file.size() < 12 || file.size() > lim::kMaxFileBytes) {
        result.error = "file is empty or larger than 64 MB";
        return result;
    }
    cgltf_options options{};
    options.type = cgltf_file_type_glb;
    cgltf_data* raw = nullptr;
    if (cgltf_parse(&options, file.data(), file.size(), &raw) != cgltf_result_success) {
        result.error = "not a valid binary glTF file";
        return result;
    }
    std::unique_ptr<cgltf_data, DataDeleter> data(raw);

    // Only the file's own binary chunk: no external or data URIs.
    if (data->buffers_count != 1 || data->buffers[0].uri != nullptr || data->bin == nullptr ||
        data->bin_size < data->buffers[0].size) {
        result.error = "the model must keep all its data inside the .glb";
        return result;
    }
    data->buffers[0].data = const_cast<void*>(data->bin);
    data->buffers[0].data_free_method = cgltf_data_free_method_none;
    if (cgltf_validate(data.get()) != cgltf_result_success) {
        result.error = "the glTF data is inconsistent";
        return result;
    }

    Builder builder(*data, result.model);
    if (!builder.build(result.error)) {
        result.model = ModelData{};
        return result;
    }
    compute_bounds(result.model);
    result.ok = true;
    return result;
}

}  // namespace sc::render
