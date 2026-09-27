// Depth-only rendering of animated characters into one shadow cascade.
#include "skinning.hlsli"

StructuredBuffer<CharacterData> characters : register(t0, space0);
StructuredBuffer<float4> bones : register(t1, space0);

cbuffer ShadowUniforms : register(b0, space1)
{
    float4x4 light_view_proj;
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

float4 main(VertexInput input) : SV_Position
{
    CharacterData c = characters[input.instance];
    float3x4 skin = skin_matrix(bones, c, input.joints, input.weights);
    float3 model_pos = mul(skin, float4(input.position, 1.0));
    return mul(light_view_proj, float4(character_transform(c, model_pos), 1.0));
}
