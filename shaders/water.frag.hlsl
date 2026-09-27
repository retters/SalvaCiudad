// Stylized water: color by depth, gentle moving ripples, sun glints, fresnel
// and the same fog as the rest of the scene.
#include "scene_common.hlsli"

cbuffer WaterUniforms : register(b0, space3)
{
    float4 sun_direction;    // xyz: towards the sun.
    float4 sun_color;
    float4 fog_color;        // rgb; a = density.
    float4 camera_position;  // xyz; w = time in seconds.
    float4 shallow_color;
    float4 deep_color;
};

struct PixelInput
{
    float4 position : SV_Position;
    float3 world_pos : TEXCOORD0;
    float depth : TEXCOORD1;
    float wet : TEXCOORD2;
};

float4 main(PixelInput input) : SV_Target0
{
    if (input.wet < 0.5)
    {
        discard;
    }
    float t = camera_position.w;
    float2 p = input.world_pos.xz;
    // Two layers of slow waves for the surface normal.
    float2 slope = float2(cos(p.x * 0.35 + t * 0.9) + cos((p.x + p.y) * 0.21 - t * 0.6),
                          cos(p.y * 0.31 - t * 0.8) + cos((p.x - p.y) * 0.27 + t * 0.7)) * 0.06;
    float3 n = normalize(float3(-slope.x, 1.0, -slope.y));

    float3 to_camera = camera_position.xyz - input.world_pos;
    float distance = length(to_camera);
    float3 v = to_camera / max(distance, 0.001);
    float3 l = normalize(sun_direction.xyz);

    float deep = saturate(input.depth / 2.5);
    float3 color = lerp(shallow_color.rgb, deep_color.rgb, deep);
    float fresnel = pow(1.0 - saturate(dot(n, v)), 4.0);
    color = lerp(color, fog_color.rgb * 0.9, fresnel * 0.6);
    float3 h = normalize(l + v);
    color += sun_color.rgb * pow(saturate(dot(n, h)), 120.0) * 0.6;

    float fog = 1.0 - exp2(-fog_color.a * distance * distance);
    color = lerp(color, fog_color.rgb, saturate(fog));
    float alpha = saturate(0.45 + deep * 0.45 + fresnel * 0.3);
    return float4(linear_to_srgb(color), alpha);
}
