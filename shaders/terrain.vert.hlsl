// Terrain: one shared grid per level of detail, placed per chunk. Heights
// and colors come from the map; the output feeds mesh.frag, so the ground
// gets the same light, shadows and fog as everything else.
#include "terrain_common.hlsli"

Texture2D<float4> ground_colors : register(t0, space0);
SamplerState ground_sampler : register(s0, space0);
StructuredBuffer<uint> heights : register(t1, space0);
StructuredBuffer<ChunkData> chunks : register(t2, space0);

cbuffer TerrainUniforms : register(b0, space1)
{
    float4x4 view_proj;
    int4 map;  // x: vertices per side, y: cells per side.
};

cbuffer LodUniforms : register(b1, space1)
{
    int4 lod;  // x: step between vertices, y: color mip level.
};

struct VertexInput
{
    float3 grid : TEXCOORD0;  // x, z in cells from the chunk origin; y: 1 on the skirt.
    uint chunk : TEXCOORD1;
};

struct VertexOutput
{
    float4 position : SV_Position;
    float3 world_pos : TEXCOORD0;
    float3 normal : TEXCOORD1;
    float2 uv : TEXCOORD2;
    float4 tint : TEXCOORD3;
};

VertexOutput main(VertexInput input)
{
    ChunkData c = chunks[input.chunk];
    int step = lod.x;
    int x = min(c.origin.x + (int)input.grid.x, map.x - 1);
    int z = min(c.origin.y + (int)input.grid.z, map.x - 1);
    float h = map_height(heights, map.x, x, z);

    // Normal from the neighbors one step away.
    float hl = map_height(heights, map.x, x - step, z);
    float hr = map_height(heights, map.x, x + step, z);
    float hd = map_height(heights, map.x, x, z - step);
    float hu = map_height(heights, map.x, x, z + step);
    float3 normal = normalize(float3(hl - hr, 2.0 * step, hd - hu));

    // Skirts hang down to hide cracks between levels of detail.
    float y = h - input.grid.y * (1.0 + 0.5 * step);

    VertexOutput output;
    output.world_pos = float3((float)x, y, (float)z);
    output.position = mul(view_proj, float4(output.world_pos, 1.0));
    output.normal = normal;
    output.uv = output.world_pos.xz / 6.0;
    float2 map_uv = (float2((float)x, (float)z)) / (float)map.y;
    output.tint = ground_colors.SampleLevel(ground_sampler, map_uv, (float)lod.y);
    return output;
}
