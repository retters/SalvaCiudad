// Instanced model vertices. The per-instance attribute is an index into the
// instance storage buffer, so only the visible indices change each frame.
#include "scene_common.hlsli"

StructuredBuffer<InstanceData> instances : register(t0, space0);

cbuffer MeshVertexUniforms : register(b0, space1)
{
    float4x4 view_proj;
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
    output.tint = inst.tint;
    return output;
}
