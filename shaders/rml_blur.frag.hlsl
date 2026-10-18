// One direction of RmlUi's blur filter (phase 118), ported from RmlUi's GL3
// renderer: seven taps `offset` apart, reading nothing outside `limits` so
// neighbouring content does not bleed in.
// Register layout follows SDL's GPU conventions for pixel shaders.

Texture2D<float4> image : register(t0, space2);
SamplerState image_sampler : register(s0, space2);

cbuffer RmlBlurUniforms : register(b0, space3)
{
    float4 weights;  // Center first.
    float4 limits;   // xy min, zw max texture coordinate.
    float2 offset;   // Between taps, in texture coordinates.
    float2 unused;
};

struct PixelInput
{
    float4 position : SV_Position;
    float2 ndc : TEXCOORD0;
    float2 uv : TEXCOORD1;
};

float4 main(PixelInput input) : SV_Target0
{
    float4 sum = float4(0.0, 0.0, 0.0, 0.0);
    [unroll] for (int i = -3; i <= 3; ++i)
    {
        const float2 uv = input.uv + float(i) * offset;
        const float2 inside = step(limits.xy, uv) * step(uv, limits.zw);
        sum += image.Sample(image_sampler, uv) * inside.x * inside.y * weights[abs(i)];
    }
    return sum;
}
