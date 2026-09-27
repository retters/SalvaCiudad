// Sky gradient with a soft sun, matching the fog color at the horizon.
#include "scene_common.hlsli"

cbuffer SkyUniforms : register(b0, space3)
{
    float4x4 inverse_view_proj;
    float4 sun_direction;  // xyz: towards the sun.
    float4 zenith_color;   // rgb, linear.
    float4 horizon_color;  // rgb, linear (same as the fog).
    float4 sun_color;      // rgb, linear.
};

struct PixelInput
{
    float4 position : SV_Position;
    float2 ndc : TEXCOORD0;
};

float4 main(PixelInput input) : SV_Target0
{
    float4 near_point = mul(inverse_view_proj, float4(input.ndc, 1.0, 1.0));
    float4 far_point = mul(inverse_view_proj, float4(input.ndc, 0.0001, 1.0));
    float3 dir = normalize(far_point.xyz / far_point.w - near_point.xyz / near_point.w);

    float up = saturate(dir.y);
    float3 color = lerp(horizon_color.rgb, zenith_color.rgb, pow(up, 0.6));
    float sun = saturate(dot(dir, normalize(sun_direction.xyz)));
    color += sun_color.rgb * (pow(sun, 600.0) * 4.0 + pow(sun, 12.0) * 0.15);
    if (dir.y < 0.0)
    {
        color = horizon_color.rgb;  // Below the horizon the fog takes over.
    }
    return float4(linear_to_srgb(tonemap(color)), 1.0);
}
