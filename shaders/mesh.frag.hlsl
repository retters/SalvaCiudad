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
    float4 texel = base_color_tex.Sample(base_sampler, input.uv);
    float3 albedo = srgb_to_linear(texel.rgb) * base_color.rgb * input.tint.rgb;
    float3 n = normalize(input.normal);
    return shade(apply_snow(albedo, n, 0.55), n, input.world_pos, input.tint.a > 1.5 ? 1.0 : 0.0);
}
