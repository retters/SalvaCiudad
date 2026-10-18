// A full-screen triangle for RmlUi's layers and filters (phase 118), from
// the vertex index alone. TEXCOORD0 is the position in clip space, as the
// engine's blur (blur.frag.hlsl) expects; TEXCOORD1 the texture coordinate,
// scaled and moved by `uv_transform` (xy scale, zw offset).
// Register layout follows SDL's GPU conventions for vertex shaders.

cbuffer RmlQuadUniforms : register(b0, space1)
{
    float4 uv_transform;
};

struct VertexOutput
{
    float4 position : SV_Position;
    float2 ndc : TEXCOORD0;
    float2 uv : TEXCOORD1;
};

VertexOutput main(uint id : SV_VertexID)
{
    const float2 ndc = float2(id == 1 ? 3.0 : -1.0, id == 2 ? 3.0 : -1.0);
    VertexOutput output;
    output.position = float4(ndc, 0.0, 1.0);
    output.ndc = ndc;
    const float2 uv = float2(ndc.x * 0.5 + 0.5, 0.5 - ndc.y * 0.5);
    output.uv = uv * uv_transform.xy + uv_transform.zw;
    return output;
}
