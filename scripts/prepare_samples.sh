#!/bin/bash

# GPL - Prepare Sample Videos Script
# ==================================

# Set colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}"
echo "======================================================"
echo "  GPL - Generative Perception Layers"
echo "  Sample Video Preparation"
echo "======================================================"
echo -e "${NC}"

# Check if ffmpeg is installed
echo -e "${BLUE}Checking dependencies...${NC}"
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}ffmpeg is not installed.${NC}"
    echo -e "${YELLOW}Please install ffmpeg:${NC}"
    echo "  macOS: brew install ffmpeg"
    echo "  Ubuntu: sudo apt-get install ffmpeg"
    exit 1
else
    echo -e "${GREEN}✓ ffmpeg is installed.${NC}"
fi

# Create samples directory
echo -e "${BLUE}Setting up data/samples directory...${NC}"
mkdir -p data/samples
echo -e "${GREEN}✓ data/samples directory is ready.${NC}"

# Check if we have any videos already
VIDEO_COUNT=$(ls -1 data/samples/*.mp4 2>/dev/null | wc -l)
if [ $VIDEO_COUNT -gt 0 ]; then
    echo -e "${GREEN}✓ Found $VIDEO_COUNT sample videos.${NC}"
    echo -e "${YELLOW}Would you like to use these or prepare new ones? (use/new)${NC}"
    read -r choice
    
    if [[ $choice == "use" ]]; then
        echo -e "${GREEN}Using existing videos.${NC}"
        exit 0
    fi
fi

# Options for sample preparation
echo -e "${BLUE}Sample Video Options:${NC}"
echo "1. Convert your own video(s)"
echo "2. Download free 4K HDR samples"
echo "3. Generate test patterns"
read -r option

if [ "$option" == "1" ]; then
    # Convert user's video
    echo -e "${BLUE}Drag and drop a video file and press Enter:${NC}"
    read -r input_file
    
    # Clean input path
    input_file=$(echo "$input_file" | sed "s/^[ \t]*//g" | sed "s/[ \t]*$//g" | sed "s/'//g")
    
    if [ ! -f "$input_file" ]; then
        echo -e "${RED}File not found: $input_file${NC}"
        exit 1
    fi
    
    filename=$(basename "$input_file")
    output_file="data/samples/sample_${filename%.*}.mp4"
    
    echo -e "${YELLOW}Converting to 4K sample...${NC}"
    
    # Convert with HDR-friendly settings
    ffmpeg -i "$input_file" \
        -c:v libx264 \
        -preset slow \
        -crf 18 \
        -vf "scale=3840:2160:force_original_aspect_ratio=decrease,pad=3840:2160:(ow-iw)/2:(oh-ih)/2" \
        -pix_fmt yuv420p10le \
        -c:a aac -b:a 192k \
        -movflags +faststart \
        -t 120 \
        "$output_file"
    
    echo -e "${GREEN}✓ Video converted: $output_file${NC}"
    
elif [ "$option" == "2" ]; then
    # Download HDR samples
    echo -e "${BLUE}Downloading HDR sample videos...${NC}"
    
    # Create temp directory
    mkdir -p tmp_downloads
    
    # Sample HDR video URLs (update with actual HDR samples)
    declare -a urls=(
        "https://www.demolandia.net/media/video/page-1/4k-hdr-video-demo.html"
    )
    
    echo -e "${YELLOW}Note: Please download HDR samples manually from:${NC}"
    echo "- https://4kmedia.org/downloads/"
    echo "- https://www.demolandia.net/"
    echo "Place them in: data/samples/"
    
elif [ "$option" == "3" ]; then
    # Generate test patterns
    echo -e "${BLUE}Generating test patterns...${NC}"
    
    # Color bars
    ffmpeg -f lavfi -i testsrc=duration=10:size=3840x2160:rate=30 \
        -pix_fmt yuv420p10le \
        "data/samples/test_colorbars_4k.mp4"
    
    # Gradient pattern
    ffmpeg -f lavfi -i "gradients=size=3840x2160:duration=10" \
        -pix_fmt yuv420p10le \
        "data/samples/test_gradient_4k.mp4"
    
    echo -e "${GREEN}✓ Test patterns generated.${NC}"
fi

# Generate telemetry test data
echo -e "${BLUE}Generating sample telemetry data...${NC}"

cat > data/samples/telemetry_example.json << EOF
{
    "ambient_light_sequence": [
        {"time": 0, "value": 50, "unit": "lux"},
        {"time": 5, "value": 200, "unit": "lux"},
        {"time": 10, "value": 1000, "unit": "lux"},
        {"time": 15, "value": 5000, "unit": "lux"},
        {"time": 20, "value": 10000, "unit": "lux"}
    ],
    "color_temperature_sequence": [
        {"time": 0, "value": 2700, "unit": "kelvin"},
        {"time": 10, "value": 5000, "unit": "kelvin"},
        {"time": 20, "value": 6500, "unit": "kelvin"}
    ],
    "motion_sequence": [
        {"time": 0, "value": 0.1, "unit": "normalized"},
        {"time": 5, "value": 0.5, "unit": "normalized"},
        {"time": 10, "value": 0.8, "unit": "normalized"},
        {"time": 15, "value": 0.3, "unit": "normalized"}
    ]
}
EOF

echo -e "${GREEN}✓ Sample telemetry data created.${NC}"

# Summary
VIDEO_COUNT=$(ls -1 data/samples/*.mp4 2>/dev/null | wc -l)
echo -e "${GREEN}"
echo "======================================================"
echo "  Setup Complete!"
echo "  - Videos ready: $VIDEO_COUNT"
echo "  - Telemetry data: data/samples/telemetry_example.json"
echo "  "
echo "  Run with: python main.py"
echo "======================================================"
echo -e "${NC}"