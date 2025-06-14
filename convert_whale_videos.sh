#!/bin/bash
# Convert all whale demo videos to web-compatible H.264

echo "Converting whale videos to H.264 for web compatibility..."

# List of videos to convert
videos=(
    "whale_standard_adaptation"
    "whale_depth_adaptation"
    "whale_underwater_color_adaptation"
    "whale_whale_motion_adaptation"
)

# Convert each video
for video in "${videos[@]}"; do
    input="data/output/${video}.mp4"
    output="data/output/${video}_web.mp4"
    
    if [ -f "$input" ]; then
        echo "Converting $video..."
        docker run --rm -v $(pwd):/app -w /app gpl \
            ffmpeg -i "$input" \
            -c:v libx264 -preset fast -crf 22 \
            -c:a aac -b:a 128k \
            -movflags +faststart \
            -y "$output"
        echo "✓ Created $output"
    else
        echo "⚠ Skipping $video (not found)"
    fi
done

echo "Done! All whale videos converted."