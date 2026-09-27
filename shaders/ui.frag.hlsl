// 2D interface: the atlas holds glyph coverage in the red channel, with an
// opaque white area for solid shapes. With `image` set, the texture is an
// RGBA picture (the minimap) tinted by the vertex color instead.
// Register layout follows SDL's GPU conventions for pixel shaders.

Texture2D<float4> atlas : register(t0, space2);
SamplerState atlas_sampler : register(s0, space2);

cbuffer UiMode : register(b0, space3)
{
    float image;
    float3 unused;
};

struct PixelInput
{
    float4 position : SV_Position;
    float2 uv : TEXCOORD0;
    float4 color : TEXCOORD1;
};

float4 main(PixelInput input) : SV_Target0
{
    float4 texel = atlas.Sample(atlas_sampler, input.uv);
    if (image > 0.5)
    {
        return input.color * texel;
    }
    return float4(input.color.rgb, input.color.a * texel.r);
}
