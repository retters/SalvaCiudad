// Faceted water over the chunks that have water. A vertex takes the highest
// water of the four cells around it; dry vertices sink under the ground so
// the shore hides the edge. Vertices are nudged and bob with slow waves, so
// the surface breaks into moving facets.
#include "terrain_common.hlsli"

StructuredBuffer<uint> heights : register(t0, space0);
StructuredBuffer<uint> water : register(t1, space0);
StructuredBuffer<ChunkData> chunks : register(t2, space0);

cbuffer TerrainUniforms : register(b0, space1)
{
    float4x4 view_proj;
    int4 map;       // x: vertices per side, y: cells per side, z: vertex step.
    float4 params;  // x: time in seconds.
};

struct VertexInput
{
    float3 grid : TEXCOORD0;
    uint chunk : TEXCOORD1;
};

struct VertexOutput
{
    float4 position : SV_Position;
    float3 world_pos : TEXCOORD0;
    float depth : TEXCOORD1;  // Water depth at this point, meters.
    float wet : TEXCOORD2;    // 1 where there is water.
};

uint hash(uint2 p)
{
    uint h = p.x * 0x8DA6B343u ^ p.y * 0xD8163841u;
    h ^= h >> 13;
    h *= 0x5BD1E995u;
    h ^= h >> 15;
    return h;
}

VertexOutput main(VertexInput input)
{
    ChunkData c = chunks[input.chunk];
    int x = min(c.origin.x + (int)input.grid.x, map.x - 1);
    int z = min(c.origin.y + (int)input.grid.z, map.x - 1);
    float ground = map_height(heights, map.x, x, z);
    float level = max(max(cell_water(water, map.y, x - 1, z - 1), cell_water(water, map.y, x, z - 1)),
                      max(cell_water(water, map.y, x - 1, z), cell_water(water, map.y, x, z)));

    VertexOutput output;
    output.wet = level > 0.0 ? 1.0 : 0.0;
    float depth = max(level - ground, 0.0);
    // Irregular facets: the same nudge for a grid point in every chunk.
    uint h = hash(uint2(x + 7000, z + 7000));
    float step = (float)map.z;
    float2 nudge = (float2((float)(h & 0xFFu), (float)((h >> 8) & 0xFFu)) / 255.0 - 0.5) * step * 0.6;
    float t = params.x;
    float wave = sin(t * 1.1 + x * 0.31 + z * 0.17) * 0.07 + sin(t * 0.7 - x * 0.13 + z * 0.29) * 0.05;
    wave *= saturate(depth * 1.5);  // Calm at the very edge.
    float y = level > 0.0 ? level - 0.08 + wave : ground - 2.0;
    output.world_pos = float3((float)x + nudge.x, y, (float)z + nudge.y);
    output.position = mul(view_proj, float4(output.world_pos, 1.0));
    output.depth = depth;
    return output;
}
