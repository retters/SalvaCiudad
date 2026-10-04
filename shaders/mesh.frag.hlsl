// Lit models: the material color times the texture and the instance tint.
#include "lighting.hlsli"

struct PixelInput
{
    float4 position : SV_Position;
    float3 world_pos : TEXCOORD0;
    float3 normal : TEXCOORD1;
    float2 uv : TEXCOORD2;
    float4 tint : TEXCOORD3;
};

float4 main(PixelInput input) : SV_Target0
{
    // A faded model (phase 61: what is in the camera's way, the ghost of
    // its anchor) is see-through by leaving pixels out in a fine pattern:
    // no blending, so the depth and the order of drawing stay as they are.
    float faded = frac(input.tint.a + 0.001);
    if (faded > 0.01)
    {
        static const float kPattern[16] = {0.5, 8.5, 2.5, 10.5, 12.5, 4.5, 14.5, 6.5,
                                           3.5, 11.5, 1.5, 9.5, 15.5, 7.5, 13.5, 5.5};
        uint2 pixel = (uint2)input.position.xy & 3u;
        if (kPattern[pixel.y * 4u + pixel.x] / 16.0 < faded)
        {
            discard;
        }
    }
    float4 texel = base_color_tex.Sample(base_sampler, input.uv);
    // The texture's format is sRGB, so the sample is already linear.
    float3 albedo = texel.rgb * base_color.rgb * input.tint.rgb;
    float3 n = normalize(input.normal);
    // The material's alpha says whether it shines: 1 no, 2 a window, 3 itself.
    float glow = max(0.0, round(base_color.a) - 1.0);
    return shade(glow > 0.5 ? albedo : apply_snow(albedo, n, 0.55), n, input.world_pos, input.tint.a > 1.9 ? 1.0 : 0.0,
                 glow);
}
