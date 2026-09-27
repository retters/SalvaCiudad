// Animated characters: skinning from baked clips, per-character palette.
// Outputs the same interface as mesh.vert, so mesh.frag lights them.
#include "skinning.hlsli"

StructuredBuffer<CharacterData> characters : register(t0, space0);
StructuredBuffer<float4> bones : register(t1, space0);
StructuredBuffer<float4> palettes : register(t2, space0);

cbuffer SkinnedVertexUniforms : register(b0, space1)
{
    float4x4 view_proj;
};

cbuffer DrawUniforms : register(b1, space1)
{
    int4 draw;  // x: palette slot of this primitive, or -1 for its own color.
};

struct VertexInput
{
    float3 position : TEXCOORD0;
    float3 normal : TEXCOORD1;
    float2 uv : TEXCOORD2;
    uint4 joints : TEXCOORD3;
    float4 weights : TEXCOORD4;
    uint instance : TEXCOORD5;
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
    CharacterData c = characters[input.instance];
    float3x4 skin = skin_matrix(bones, c, input.joints, input.weights);
    float3 model_pos = mul(skin, float4(input.position, 1.0));
    float3 model_normal = mul((float3x3)skin, input.normal);

    VertexOutput output;
    output.world_pos = character_transform(c, model_pos);
    output.position = mul(view_proj, float4(output.world_pos, 1.0));
    output.normal = normalize(character_rotate(c, model_normal));
    output.uv = input.uv;
    output.tint = draw.x >= 0 ? palettes[c.anim.w * 8 + (uint)draw.x] : float4(1.0, 1.0, 1.0, 1.0);
    return output;
}
