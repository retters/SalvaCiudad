// 2D interface: the atlas holds glyph coverage in the red channel, with an
// opaque white area for solid shapes.
// Register layout follows SDL's GPU conventions for pixel shaders.

Texture2D<float4> atlas : register(t0, space2);
SamplerState atlas_sampler : register(s0, space2);

struct PixelInput
{
    float4 position : SV_Position;
    float2 uv : TEXCOORD0;
    float4 color : TEXCOORD1;
};

float4 main(PixelInput input) : SV_Target0
{
    float coverage = atlas.Sample(atlas_sampler, input.uv).r;
    return float4(input.color.rgb, input.color.a * coverage);
}
