// Decorative grass: a grid of tufts around the camera, placed entirely on
// the GPU. Each grid cell hashes to a jittered tuft; the ground color
// texture's alpha says how much grass grows there. Feeds mesh.frag.
#include "terrain_common.hlsli"

Texture2D<float4> ground_colors : register(t0, space0);
SamplerState ground_sampler : register(s0, space0);
StructuredBuffer<uint> heights : register(t1, space0);
StructuredBuffer<uint> water : register(t2, space0);

cbuffer GrassUniforms : register(b0, space1)
{
    float4x4 view_proj;
    int4 map;       // x: vertices per side, y: cells per side, z: tufts per grid side.
    float4 grid;    // xy: world position of the grid's first cell, z: spacing, w: far distance.
    float4 camera;  // xyz: eye, w: time in seconds.
};

struct VertexInput
{
    float3 position : TEXCOORD0;  // Tuft vertex; y from 0 (root) to 1 (tip).
    uint instance : SV_InstanceID;
};

struct VertexOutput
{
    float4 position : SV_Position;
    float3 world_pos : TEXCOORD0;
    float3 normal : TEXCOORD1;
    float2 uv : TEXCOORD2;
    float4 tint : TEXCOORD3;
};

uint hash(uint2 p)
{
    uint h = p.x * 0x8DA6B343u ^ p.y * 0xD8163841u;
    h ^= h >> 13;
    h *= 0x5BD1E995u;
    h ^= h >> 15;
    return h;
}

float unit(uint h, uint shift)
{
    return (float)((h >> shift) & 0xFFu) / 255.0;
}

float ground_height(float2 p)
{
    int2 i = (int2)floor(p);
    float2 f = p - (float2)i;
    float a = map_height(heights, map.x, i.x, i.y);
    float b = map_height(heights, map.x, i.x + 1, i.y);
    float c = map_height(heights, map.x, i.x, i.y + 1);
    float d = map_height(heights, map.x, i.x + 1, i.y + 1);
    return lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y);
}

VertexOutput main(VertexInput input)
{
    uint side = (uint)map.z;
    uint2 cell_local = uint2(input.instance % side, input.instance / side);
    float spacing = grid.z;
    float2 cell_world = grid.xy + (float2)cell_local * spacing;
    uint h = hash((uint2)(int2)round(cell_world / spacing) + uint2(40000, 40000));
    float2 base = cell_world + float2(unit(h, 0), unit(h, 8)) * spacing;

    float cells = (float)map.y;
    float4 ground = ground_colors.SampleLevel(ground_sampler, base / cells, 0.0);
    float3 root = float3(base.x, ground_height(base), base.y);
    float dist = length(root - camera.xyz);
    // Thin out with the density, and shrink away toward the far edge.
    float grow = step(unit(h, 16), ground.a);
    float fade = saturate((grid.w - dist) / (grid.w * 0.35));
    bool inside = all(base >= 0.0) && all(base < cells);
    int2 c = (int2)floor(base);
    bool wet = cell_water(water, map.y, c.x, c.y) > 0.0;
    float size = (inside && !wet) ? grow * fade * (0.7 + 0.6 * unit(h, 24)) : 0.0;

    float angle = unit(h, 4) * 6.2831853;
    float s = sin(angle);
    float co = cos(angle);
    float3 p = input.position * size;
    p.xz = float2(p.x * co - p.z * s, p.x * s + p.z * co);
    // A gentle sway, stronger at the tips.
    float sway = sin(camera.w * 1.7 + base.x * 0.35 + base.y * 0.23) * 0.06 * input.position.y * size;
    p.x += sway;
    p.z += sway * 0.5;

    VertexOutput output;
    output.world_pos = root + p;
    output.position = mul(view_proj, float4(output.world_pos, 1.0));
    output.normal = normalize(float3(p.x * 0.3, 1.0, p.z * 0.3));
    output.uv = float2(0.0, 0.0);
    // The ground's own color, lighter toward the tips, a little varied.
    float shade = (0.55 + 0.8 * input.position.y) * (0.85 + 0.2 * unit(h, 12));
    output.tint = float4(ground.rgb * shade, 1.0);
    return output;
}
