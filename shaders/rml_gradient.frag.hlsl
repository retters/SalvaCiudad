// RmlUi's gradient decorators (phase 118): linear, radial and conic, plain
// or repeating, ported from RmlUi's GL3 renderer. Colors are premultiplied.
// Register layout follows SDL's GPU conventions for pixel shaders.

cbuffer RmlGradientUniforms : register(b0, space3)
{
    int func;        // 0 linear, 1 radial, 2 conic; +3 repeating.
    int num_stops;
    float2 p;        // linear: start; radial and conic: center.
    float2 v;        // linear: start to end; radial: inverse radius; conic: angle as a unit vector.
    float2 unused;
    float4 stop_colors[16];
    float4 stop_positions[4];  // 16 positions, four per element.
};

struct PixelInput
{
    float4 position : SV_Position;
    float4 color : TEXCOORD0;
    float2 uv : TEXCOORD1;
};

float stop_position(int i)
{
    return stop_positions[i / 4][i % 4];
}

float4 mix_stop_colors(float t)
{
    float4 color = stop_colors[0];
    for (int i = 1; i < num_stops; i++)
    {
        color = lerp(color, stop_colors[i], smoothstep(stop_position(i - 1), stop_position(i), t));
    }
    return color;
}

float4 main(PixelInput input) : SV_Target0
{
    const float pi = 3.14159265;
    const int kind = func % 3;
    float t = 0.0;
    if (kind == 0)
    {
        t = dot(v, input.uv - p) / dot(v, v);
    }
    else if (kind == 1)
    {
        t = length(v * (input.uv - p));
    }
    else
    {
        const float2 d = input.uv - p;
        const float2 r = float2(v.x * d.x + v.y * d.y, -v.y * d.x + v.x * d.y);
        t = 0.5 + atan2(-r.x, r.y) / (2.0 * pi);
    }
    if (func >= 3)
    {
        const float t0 = stop_position(0);
        const float span = stop_position(num_stops - 1) - t0;
        if (span > 0.0)
        {
            const float x = t - t0;
            t = t0 + (x - span * floor(x / span));
        }
    }
    return input.color * mix_stop_colors(t);
}
