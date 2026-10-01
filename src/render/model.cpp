#include "render/model.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <format>
#include <memory>

#include <cgltf.h>
#include <stb_image.h>
#include <yyjson.h>

#include "core/json.h"

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

// --- Skeletons and animations --------------------------------------------

struct Trs {
    math::Vec3 t{0, 0, 0};
    float q[4] = {0, 0, 0, 1};  // x, y, z, w
    math::Vec3 s{1, 1, 1};
};

Trs node_rest(const cgltf_node& n) {
    Trs r;
    if (n.has_translation) r.t = {n.translation[0], n.translation[1], n.translation[2]};
    if (n.has_rotation) std::copy(n.rotation, n.rotation + 4, r.q);
    if (n.has_scale) r.s = {n.scale[0], n.scale[1], n.scale[2]};
    return r;
}

math::Mat4 trs_matrix(const Trs& trs) {
    float len = std::sqrt(trs.q[0] * trs.q[0] + trs.q[1] * trs.q[1] + trs.q[2] * trs.q[2] + trs.q[3] * trs.q[3]);
    if (!(len > 0.0f)) {
        len = 1.0f;
    }
    return math::translation(trs.t) *
           math::rotation_quat(trs.q[0] / len, trs.q[1] / len, trs.q[2] / len, trs.q[3] / len) * math::scaling(trs.s);
}

// Reads a channel's value at time t. Returns false for malformed data.
bool sample_channel(const cgltf_animation_sampler& s, float t, int comps, float out[4]) {
    const cgltf_accessor* in = s.input;
    const cgltf_accessor* val = s.output;
    const bool cubic = s.interpolation == cgltf_interpolation_type_cubic_spline;
    if (in == nullptr || val == nullptr || in->count == 0 || in->type != cgltf_type_scalar ||
        val->count != in->count * (cubic ? 3 : 1) || cgltf_num_components(val->type) != static_cast<cgltf_size>(comps)) {
        return false;
    }
    // Find the key interval (keys are few; a linear scan is fine).
    cgltf_size i = 0;
    float t0 = 0.0f;
    float t1 = 0.0f;
    if (!cgltf_accessor_read_float(in, 0, &t0, 1)) {
        return false;
    }
    while (i + 1 < in->count) {
        if (!cgltf_accessor_read_float(in, i + 1, &t1, 1)) {
            return false;
        }
        if (t1 > t) {
            break;
        }
        t0 = t1;
        ++i;
    }
    const auto read = [&](cgltf_size key, float* v) {
        return cgltf_accessor_read_float(val, cubic ? key * 3 + 1 : key, v, static_cast<cgltf_size>(comps));
    };
    float a[4] = {0, 0, 0, 0};
    if (!read(i, a)) {
        return false;
    }
    std::copy(a, a + comps, out);
    if (i + 1 >= in->count || s.interpolation == cgltf_interpolation_type_step || t <= t0) {
        return true;
    }
    float b[4] = {0, 0, 0, 0};
    if (!read(i + 1, b)) {
        return false;
    }
    const float span = t1 - t0;
    const float f = span > 0.0f ? std::clamp((t - t0) / span, 0.0f, 1.0f) : 0.0f;
    if (comps == 4) {
        // Normalized linear blend along the shortest arc; fine for keys a
        // frame apart.
        const float d = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
        const float sign = d < 0.0f ? -1.0f : 1.0f;
        float len = 0.0f;
        for (int c = 0; c < 4; ++c) {
            out[c] = a[c] + (b[c] * sign - a[c]) * f;
            len += out[c] * out[c];
        }
        len = std::sqrt(len);
        for (int c = 0; c < 4 && len > 0.0f; ++c) {
            out[c] /= len;
        }
    } else {
        for (int c = 0; c < comps; ++c) {
            out[c] = a[c] + (b[c] - a[c]) * f;
        }
    }
    return true;
}

class Builder {
public:
    Builder(const cgltf_data& data, ModelData& model) : data_(data), model_(model) {}

    bool build(std::string& error) {
        if (!load_materials(error) || !load_skin(error)) {
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
        return skin_ == nullptr || bake_clips(error);
    }

private:
    bool load_skin(std::string& error) {
        if (data_.skins_count == 0) {
            return true;
        }
        if (data_.skins_count > 1) {
            error = "only one skeleton per model is supported";
            return false;
        }
        skin_ = &data_.skins[0];
        const cgltf_size count = skin_->joints_count;
        if (count == 0 || count > lim::kMaxJoints) {
            error = "the skeleton has no joints or more than 64";
            return false;
        }
        for (cgltf_size j = 0; j < count; ++j) {
            const cgltf_node* n = skin_->joints[j];
            const std::string name = n->name != nullptr ? n->name : std::format("joint{}", j);
            if (name.size() > 64 || model_.joint_index(name) >= 0) {
                error = "joint names must be unique and short";
                return false;
            }
            model_.joint_names.push_back(name);
            math::Mat4 inverse_bind = math::Mat4::identity();
            if (skin_->inverse_bind_matrices != nullptr) {
                float m[16];
                if (skin_->inverse_bind_matrices->count != count ||
                    !cgltf_accessor_read_float(skin_->inverse_bind_matrices, j, m, 16)) {
                    error = "invalid inverse bind matrices";
                    return false;
                }
                inverse_bind = to_mat4(m);
            }
            inverse_bind_.push_back(inverse_bind);
            model_.joint_rest.push_back(math::inverse(inverse_bind));
        }
        for (cgltf_size j = 0; j < count; ++j) {
            model_.joint_parent.push_back(joint_of(skin_->joints[j]->parent));
        }
        return true;
    }

    // The speed a clip asks for: "<clip>_speed" in the extras of a node above
    // the skeleton (Blender writes the armature's custom properties there).
    // Anything missing, malformed or out of range means no speed.
    [[nodiscard]] float clip_speed(const std::string& clip) const {
        const std::string key = clip + "_speed";
        int depth = 0;
        for (const cgltf_node* n = skin_->joints[0]->parent; n != nullptr && depth < 64; n = n->parent, ++depth) {
            if (n->extras.data == nullptr) {
                continue;
            }
            const std::string_view text(n->extras.data);
            if (text.size() > lim::kMaxExtrasBytes) {
                continue;
            }
            const json::ParseResult parsed = json::parse_object(text);
            if (parsed.error != json::ParseError::None) {
                continue;
            }
            double speed = 0.0;
            if (json::get_double(yyjson_mut_doc_get_root(parsed.doc.get()), key.c_str(), 0.0,
                                 static_cast<double>(lim::kMaxClipSpeed), speed) == json::Field::Ok) {
                return static_cast<float>(speed);
            }
        }
        return 0.0f;
    }

    [[nodiscard]] int joint_of(const cgltf_node* n) const {
        for (cgltf_size j = 0; skin_ != nullptr && j < skin_->joints_count; ++j) {
            if (skin_->joints[j] == n) {
                return static_cast<int>(j);
            }
        }
        return -1;
    }

    // Global transform of joint `j` for this frame's local transforms.
    math::Mat4 global_of(int j, const std::vector<math::Mat4>& local, std::vector<math::Mat4>& global,
                         std::vector<char>& done, int depth) const {
        if (done[static_cast<std::size_t>(j)] != 0) {
            return global[static_cast<std::size_t>(j)];
        }
        const cgltf_node* parent = skin_->joints[j]->parent;
        math::Mat4 parent_m = math::Mat4::identity();
        const int pj = joint_of(parent);
        if (pj >= 0 && depth < 64) {
            parent_m = global_of(pj, local, global, done, depth + 1);
        } else if (parent != nullptr) {
            float w[16];
            cgltf_node_transform_world(parent, w);
            parent_m = to_mat4(w);
        }
        global[static_cast<std::size_t>(j)] = parent_m * local[static_cast<std::size_t>(j)];
        done[static_cast<std::size_t>(j)] = 1;
        return global[static_cast<std::size_t>(j)];
    }

    bool bake_clips(std::string& error) {
        const cgltf_size joints = skin_->joints_count;
        if (data_.animations_count > lim::kMaxClips) {
            error = "too many animations";
            return false;
        }
        for (cgltf_size a = 0; a < data_.animations_count; ++a) {
            const cgltf_animation& anim = data_.animations[a];
            float duration = 0.0f;
            for (cgltf_size c = 0; c < anim.samplers_count; ++c) {
                const cgltf_accessor* in = anim.samplers[c].input;
                if (in != nullptr && in->has_max) {
                    duration = std::max(duration, in->max[0]);
                }
            }
            if (!std::isfinite(duration) || duration < 0.0f ||
                duration * lim::kClipFps > static_cast<float>(lim::kMaxClipFrames)) {
                error = "animation too long or with invalid times";
                return false;
            }
            ModelClip clip;
            clip.name = anim.name != nullptr ? anim.name : std::format("clip{}", a);
            clip.fps = lim::kClipFps;
            clip.speed = clip_speed(clip.name);
            // A loop's last key repeats the first, so it is not a frame of its own.
            clip.frame_count = std::max(1, static_cast<int>(std::lround(duration * lim::kClipFps)));
            clip.skin.reserve(static_cast<std::size_t>(clip.frame_count) * joints);

            std::vector<math::Mat4> local(joints);
            std::vector<math::Mat4> global(joints);
            std::vector<char> done(joints);
            for (int f = 0; f < clip.frame_count; ++f) {
                const float t = static_cast<float>(f) / lim::kClipFps;
                for (cgltf_size j = 0; j < joints; ++j) {
                    const cgltf_node* n = skin_->joints[j];
                    if (n->has_matrix) {
                        local[j] = to_mat4(n->matrix);
                        continue;
                    }
                    Trs trs = node_rest(*n);
                    for (cgltf_size c = 0; c < anim.channels_count; ++c) {
                        const cgltf_animation_channel& ch = anim.channels[c];
                        if (ch.target_node != n || ch.sampler == nullptr) {
                            continue;
                        }
                        float v[4] = {0, 0, 0, 0};
                        bool ok = true;
                        switch (ch.target_path) {
                            case cgltf_animation_path_type_translation:
                                ok = sample_channel(*ch.sampler, t, 3, v);
                                trs.t = {v[0], v[1], v[2]};
                                break;
                            case cgltf_animation_path_type_rotation:
                                ok = sample_channel(*ch.sampler, t, 4, v);
                                std::copy(v, v + 4, trs.q);
                                break;
                            case cgltf_animation_path_type_scale:
                                ok = sample_channel(*ch.sampler, t, 3, v);
                                trs.s = {v[0], v[1], v[2]};
                                break;
                            default:
                                break;
                        }
                        if (!ok) {
                            error = "malformed animation channel";
                            return false;
                        }
                    }
                    local[j] = trs_matrix(trs);
                }
                std::fill(done.begin(), done.end(), 0);
                for (cgltf_size j = 0; j < joints; ++j) {
                    clip.skin.push_back(global_of(static_cast<int>(j), local, global, done, 0) * inverse_bind_[j]);
                }
            }
            model_.clips.push_back(std::move(clip));
        }
        return true;
    }

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
        if (m.name != nullptr) {
            out.name = std::string(m.name).substr(0, 64);
        }
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
            math::Mat4 m = math::Mat4::identity();
            if (skin_ != nullptr) {
                // Skinned vertices are placed by the joints alone; the mesh
                // node's own transform does not apply (glTF 2.0, 3.7.3).
                if (node.skin != skin_) {
                    error = "a model cannot mix skinned and rigid meshes";
                    return false;
                }
            } else {
                cgltf_float world[16];
                cgltf_node_transform_world(&node, world);
                m = to_mat4(world);
            }
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
        const cgltf_accessor* joints = nullptr;
        const cgltf_accessor* weights = nullptr;
        for (cgltf_size a = 0; a < prim.attributes_count; ++a) {
            const cgltf_attribute& attr = prim.attributes[a];
            if (attr.type == cgltf_attribute_type_position && attr.index == 0) pos = attr.data;
            if (attr.type == cgltf_attribute_type_normal && attr.index == 0) nrm = attr.data;
            if (attr.type == cgltf_attribute_type_texcoord && attr.index == 0) uv = attr.data;
            if (attr.type == cgltf_attribute_type_joints && attr.index == 0) joints = attr.data;
            if (attr.type == cgltf_attribute_type_weights && attr.index == 0) weights = attr.data;
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
        if (skin_ != nullptr && (joints == nullptr || weights == nullptr || joints->type != cgltf_type_vec4 ||
                                 weights->type != cgltf_type_vec4 || joints->count != count || weights->count != count)) {
            error = "a skinned primitive needs four joints and weights per vertex";
            return false;
        }
        if (skin_ != nullptr && !read_skin(joints, weights, count, error)) {
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

    bool read_skin(const cgltf_accessor* joints, const cgltf_accessor* weights, cgltf_size count, std::string& error) {
        for (cgltf_size i = 0; i < count; ++i) {
            cgltf_uint j[4] = {0, 0, 0, 0};
            float w[4] = {0, 0, 0, 0};
            if (!cgltf_accessor_read_uint(joints, i, j, 4) || !cgltf_accessor_read_float(weights, i, w, 4)) {
                error = "unreadable joints or weights";
                return false;
            }
            float sum = 0.0f;
            for (int k = 0; k < 4; ++k) {
                if (j[k] >= skin_->joints_count || !std::isfinite(w[k]) || w[k] < 0.0f) {
                    error = "joint index out of range or invalid weight";
                    return false;
                }
                sum += w[k];
            }
            JointWeights jw;
            if (sum <= 0.0f) {
                model_.skin.push_back(jw);  // Unweighted: follows joint 0.
                continue;
            }
            // Quantize to 1/255 so the four weights still add up to 255.
            int total = 0;
            int largest = 0;
            for (int k = 0; k < 4; ++k) {
                jw.joints[k] = static_cast<std::uint8_t>(j[k]);
                const int q = static_cast<int>(std::lround(w[k] / sum * 255.0f));
                jw.weights[k] = static_cast<std::uint8_t>(q);
                total += q;
                if (w[k] > w[largest]) {
                    largest = k;
                }
            }
            jw.weights[largest] = static_cast<std::uint8_t>(jw.weights[largest] + (255 - total));
            model_.skin.push_back(jw);
        }
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
    const cgltf_skin* skin_ = nullptr;
    std::vector<math::Mat4> inverse_bind_;
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

int ModelData::joint_index(std::string_view name) const {
    for (std::size_t i = 0; i < joint_names.size(); ++i) {
        if (joint_names[i] == name) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

int ModelData::clip_index(std::string_view name) const {
    for (std::size_t i = 0; i < clips.size(); ++i) {
        if (clips[i].name == name) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

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
