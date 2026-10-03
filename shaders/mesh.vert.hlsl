// Instanced model vertices. The per-instance attribute is an index into the
// instance storage buffer, so only the visible indices change each frame.
#include "scene_common.hlsli"

StructuredBuffer<InstanceData> instances : register(t0, space0);
StructuredBuffer<float4> building_palettes : register(t1, space0);

cbuffer MeshVertexUniforms : register(b0, space1)
{
    float4x4 view_proj;
};

cbuffer MeshDrawUniforms : register(b1, space1)
{
    int4 draw;          // x: building palette slot of this primitive, or -1.
    float4 base_color;  // The material's own color, which a palette replaces.
};

struct VertexInput
{
    float3 position : TEXCOORD0;
    float3 normal : TEXCOORD1;
    float2 uv : TEXCOORD2;
    uint instance : TEXCOORD3;
};

struct VertexOutput
{
    float4 position : SV_Position;
    float3 world_pos : TEXCOORD0;
    float3 normal : TEXCOORD1;
    float2 uv : TEXCOORD2;
    float4 tint : TEXCOORD3;
};

VertexOutput main(VertexInput input)
{
    InstanceData inst = instances[input.instance];
    VertexOutput output;
    output.world_pos = instance_transform(inst, input.position);
    output.position = mul(view_proj, float4(output.world_pos, 1.0));
    output.normal = normalize(instance_rotate(inst, input.normal));
    output.uv = input.uv;
    // A building palette (tint.w, from 1) replaces the colors of the
    // materials named after its slots; the fragment shader multiplies by
    // the material color, so divide it out here.
    // tint.w: the palette, plus 4096 for a landmark (phase 34), plus 8192
    // for each quarter it is faded (phase 61). The fragment shader gets 1,
    // or 2 for a landmark, plus the faded share.
    uint packed = (uint)inst.tint.w;
    uint palette = packed & 4095u;
    float faded = (float)((packed >> 13) & 3u) * 0.25;
    output.tint = float4(inst.tint.rgb, ((packed & 4096u) != 0u ? 2.0 : 1.0) + faded);
    if (draw.x >= 0 && palette > 0)
    {
        float3 color = building_palettes[(palette - 1) * 4 + (uint)draw.x].rgb;
        output.tint.rgb *= color / max(base_color.rgb, 0.01);
    }
    return output;
}
