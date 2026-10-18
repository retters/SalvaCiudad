// RmlUi's layer copies and filters (phase 118), ported from RmlUi's GL3
// renderer, all with premultiplied alpha. `mode`:
//   0 copy, times `factor` (opacity; 0 clears),
//   1 color matrix (rgb only, in premultiplied space),
//   2 drop shadow: the alpha inside `limits`, as `color`,
//   3 mask: times the alpha of the second texture.
// Register layout follows SDL's GPU conventions for pixel shaders.

Texture2D<float4> image : register(t0, space2);
Texture2D<float4> mask : register(t1, space2);
SamplerState image_sampler : register(s0, space2);
SamplerState mask_sampler : register(s1, space2);

cbuffer RmlPostUniforms : register(b0, space3)
{
    float mode;
    float factor;
    float2 unused;
    float4 color;
    float4 limits;  // xy min, zw max texture coordinate.
    float4x4 color_matrix;
};

struct PixelInput
{
    float4 position : SV_Position;
    float2 ndc : TEXCOORD0;
    float2 uv : TEXCOORD1;
};

float4 main(PixelInput input) : SV_Target0
{
    if (mode > 2.5)
    {
        return image.Sample(image_sampler, input.uv) * mask.Sample(mask_sampler, input.uv).a;
    }
    if (mode > 1.5)
    {
        const float2 inside = step(limits.xy, input.uv) * step(input.uv, limits.zw);
        return image.Sample(image_sampler, input.uv).a * inside.x * inside.y * color;
    }
    const float4 texel = image.Sample(image_sampler, input.uv);
    if (mode > 0.5)
    {
        return float4(mul(color_matrix, texel).rgb, texel.a);
    }
    return texel * factor;
}
