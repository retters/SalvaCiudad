// RmlUi geometry (phase 117): pixel coordinates, moved by the draw's
// translation and transform, to clip space. `transform` already holds the
// projection (pixels to clip space) times RmlUi's own transform.
// Register layout follows SDL's GPU conventions for vertex shaders.

cbuffer RmlVertexUniforms : register(b0, space1)
{
    float4x4 transform;
    float2 translation;
    float2 unused;
};

struct VertexInput
{
    float2 position : TEXCOORD0;
    float4 color : TEXCOORD1;
    float2 uv : TEXCOORD2;
};

struct VertexOutput
{
    float4 position : SV_Position;
    float4 color : TEXCOORD0;
    float2 uv : TEXCOORD1;
};

VertexOutput main(VertexInput input)
{
    VertexOutput output;
    output.position = mul(transform, float4(input.position + translation, 0.0, 1.0));
    output.color = input.color;
    output.uv = input.uv;
    return output;
}
