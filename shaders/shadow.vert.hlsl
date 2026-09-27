// Depth-only rendering of instances into one shadow cascade.
#include "scene_common.hlsli"

StructuredBuffer<InstanceData> instances : register(t0, space0);

cbuffer ShadowUniforms : register(b0, space1)
{
    float4x4 light_view_proj;
};

struct VertexInput
{
    float3 position : TEXCOORD0;
    float3 normal : TEXCOORD1;
    float2 uv : TEXCOORD2;
    uint instance : TEXCOORD3;
};

float4 main(VertexInput input) : SV_Position
{
    InstanceData inst = instances[input.instance];
    return mul(light_view_proj, float4(instance_transform(inst, input.position), 1.0));
}
