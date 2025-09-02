# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Check if .env file exists (fail build early if missing)
COPY .env* ./
RUN if [ ! -f ".env" ]; then \
        echo ""; \
        echo "❌ ERROR: .env file is required but not found!"; \
        echo ""; \
        echo "💡 Please create a .env file in the project root before building."; \
        echo "   You can use .env.example as a template:"; \
        echo ""; \
        echo "   cp .env.example .env"; \
        echo "   # Edit .env with your configuration"; \
        echo ""; \
        echo "🔧 Required configurations:"; \
        echo "   - HOST=0.0.0.0"; \
        echo "   - PORT=9004"; \
        echo "   - COMFYUI_BASE_URL=http://your-comfyui:8188"; \
        echo "   - At least one LLM API key (OPENAI_API_KEY, etc.)"; \
        echo ""; \
        exit 1; \
    fi

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY pixelle/ ./pixelle/
COPY workflows/ ./workflows/
COPY docs/ ./docs/

# Install Python dependencies using uv
RUN uv sync --frozen

# Create pixelle config directory
RUN mkdir -p /root/.pixelle

# Set default port
ENV PORT=9004

# Expose port
EXPOSE 9004

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9004/health || exit 1

# Run the application
CMD ["uv", "run", "pixelle", "start"]
