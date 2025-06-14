#!/bin/bash
# Convert all demo videos to web-compatible H.264

echo "Converting all videos to H.264 for web compatibility..."

# List of videos to convert
videos=(
    "demo_standard_adaptation"
    "demo_light_adaptation"
    "demo_color_adaptation"
    "demo_motion_adaptation"
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

echo "Done! All videos converted."