// Water surface over the chunks that have water. A vertex takes the highest
// water of the four cells around it; dry vertices sink under the ground so
// the shore hides the edge.
#include "terrain_common.hlsli"

StructuredBuffer<uint> heights : register(t0, space0);
StructuredBuffer<uint> water : register(t1, space0);
StructuredBuffer<ChunkData> chunks : register(t2, space0);

cbuffer TerrainUniforms : register(b0, space1)
{
    float4x4 view_proj;
    int4 map;  // x: vertices per side, y: cells per side.
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
    float y = level > 0.0 ? level - 0.05 : ground - 2.0;
    output.world_pos = float3((float)x, y, (float)z);
    output.position = mul(view_proj, float4(output.world_pos, 1.0));
    output.depth = max(level - ground, 0.0);
    return output;
}
