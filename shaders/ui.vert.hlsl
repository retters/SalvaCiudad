// 2D interface: pixel coordinates to clip space.
// Register layout follows SDL's GPU conventions for vertex shaders.

cbuffer UiUniforms : register(b0, space1)
{
    float2 screen_size;
    float2 unused;
};

struct VertexInput
{
    float2 position : TEXCOORD0;
    float2 uv : TEXCOORD1;
    float4 color : TEXCOORD2;
};

struct VertexOutput
{
    float4 position : SV_Position;
    float2 uv : TEXCOORD0;
    float4 color : TEXCOORD1;
};

VertexOutput main(VertexInput input)
{
    VertexOutput output;
    float2 ndc = input.position / screen_size * 2.0 - 1.0;
    output.position = float4(ndc.x, -ndc.y, 0.0, 1.0);
    output.uv = input.uv;
    output.color = input.color;
    return output;
}
