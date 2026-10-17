// RmlUi geometry (phase 117). Colors and textures arrive with premultiplied
// alpha, as RmlUi works. `mode`: 0 color only, 1 an RGBA texture, 2 the glyph
// atlas, whose red channel is the coverage.
// Register layout follows SDL's GPU conventions for pixel shaders.

Texture2D<float4> image : register(t0, space2);
SamplerState image_sampler : register(s0, space2);

cbuffer RmlFragmentUniforms : register(b0, space3)
{
    float mode;
    float3 unused;
};

struct PixelInput
{
    float4 position : SV_Position;
    float4 color : TEXCOORD0;
    float2 uv : TEXCOORD1;
};

float4 main(PixelInput input) : SV_Target0
{
    if (mode < 0.5)
    {
        return input.color;
    }
    float4 texel = image.Sample(image_sampler, input.uv);
    if (mode > 1.5)
    {
        return input.color * texel.r;
    }
    return input.color * texel;
}
