// Faceted low-poly water: flat facets (normal from screen-space
// derivatives), turquoise getting deeper with depth, see-through at the
// shore, a glint of sun on facets that face it, and the scene's fog.
#include "scene_common.hlsli"

cbuffer WaterUniforms : register(b0, space3)
{
    float4 sun_direction;    // xyz: towards the sun.
    float4 sun_color;        // rgb; a = how bright the water's own colors are.
    float4 fog_color;        // rgb; a = density.
    float4 camera_position;  // xyz; w = time in seconds.
    float4 shallow_color;
    float4 deep_color;
    float4 war_params;       // Fog of war: see apply_war_fog().
};

Texture2D<float> war_fog_tex : register(t0, space2);
Texture2D<float> war_ceiling_tex : register(t1, space2);
SamplerState war_sampler : register(s0, space2);
SamplerState war_ceiling_sampler : register(s1, space2);

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
    float3 n = normalize(cross(ddy(input.world_pos), ddx(input.world_pos)));
    if (n.y < 0.0)
    {
        n = -n;
    }
    float3 to_camera = camera_position.xyz - input.world_pos;
    float distance = length(to_camera);
    float3 v = to_camera / max(distance, 0.001);
    float3 l = normalize(sun_direction.xyz);

    float deep = saturate(input.depth / 2.0);
    float3 color = lerp(shallow_color.rgb, deep_color.rgb, deep);
    // Facets turned to the sun are lighter, the others a little darker.
    float facing = saturate(dot(n, l));
    color *= 0.8 + 0.35 * facing;
    float fresnel = pow(1.0 - saturate(dot(n, v)), 3.0);
    color = lerp(color, float3(0.85, 0.95, 1.0), fresnel * 0.35) * sun_color.a;
    float3 h = normalize(l + v);
    color += sun_color.rgb * pow(saturate(dot(n, h)), 60.0) * 0.35;

    float fog = 1.0 - exp2(-fog_color.a * distance * distance);
    color = lerp(color, fog_color.rgb, saturate(fog));
    float war = 1.0;
    if (war_params.y > 0.5)
    {
        war = war_fog_value(war_fog_tex, war_sampler, input.world_pos.xz, war_params);
        float lift = war_lift(war_ceiling_tex, war_ceiling_sampler, input.world_pos, war_params);
        color = apply_war_fog(color, war, lift, war_params);
    }
    // Clear at the shore, where the sandy bed shows through.
    float alpha = saturate(0.62 + deep * 0.33 + fresnel * 0.15);
    alpha = lerp(1.0, alpha, saturate(war * 2.0));  // Unexplored water hides the bed too.
    return float4(linear_to_srgb(tonemap(color)), alpha);
}
