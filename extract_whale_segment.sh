#!/bin/bash
# Extract 3-10 second segment from whale video

echo "Extracting whale video segment (3-10 seconds)..."

# Input and output paths
input_4k="data/samples/sdr/Sony Whale in Tonga HDR UHD 4K Demo_sdr.mp4"
input_1080p="data/samples/sdr/1080p/whale_tonga_1080p.mp4"

output_4k="data/samples/whale_3-10s_4k.mp4"
output_1080p="data/samples/sdr/1080p/whale_3-10s_1080p.mp4"

# Check if 4K version exists
if [ -f "$input_4k" ]; then
    echo "Extracting 4K version..."
    docker run --rm -v $(pwd):/app -w /app gpl \
        ffmpeg -i "$input_4k" \
        -ss 3 -t 7 \
        -c copy \
        -y "$output_4k"
    echo "✓ Created $output_4k"
else
    echo "⚠ 4K version not found at: $input_4k"
fi

# Check if 1080p version exists
if [ -f "$input_1080p" ]; then
    echo "Extracting 1080p version..."
    docker run --rm -v $(pwd):/app -w /app gpl \
        ffmpeg -i "$input_1080p" \
        -ss 3 -t 7 \
        -c copy \
        -y "$output_1080p"
    echo "✓ Created $output_1080p"
else
    echo "⚠ 1080p version not found at: $input_1080p"
    
    # Create 1080p from 4K if needed
    if [ -f "$output_4k" ]; then
        echo "Creating 1080p from 4K..."
        mkdir -p data/samples/sdr/1080p
        docker run --rm -v $(pwd):/app -w /app gpl \
            ffmpeg -i "$output_4k" \
            -vf scale=1920:1080 \
            -c:v libx264 -preset fast -crf 22 \
            -c:a copy \
            -y "$output_1080p"
        echo "✓ Created 1080p version"
    fi
fi

echo "Done! Whale segments ready for processing."