// Faceted terrain: vertices come ready in world space from the adaptive
// triangulation; the color of each facet is looked up in the pixel shader.
cbuffer FacetUniforms : register(b0, space1)
{
    float4x4 view_proj;
    float4 map;  // x: cells per side.
};

struct VertexInput
{
    float3 position : TEXCOORD0;
};

struct VertexOutput
{
    float4 position : SV_Position;
    float3 world_pos : TEXCOORD0;
};

VertexOutput main(VertexInput input)
{
    VertexOutput output;
    output.world_pos = input.position;
    output.position = mul(view_proj, float4(input.position, 1.0));
    return output;
}
