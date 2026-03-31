# Use a lightweight python base image
FROM python:3.10-slim

# Install basic system dependencies required by scientific libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy and install Python dependencies first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the Sentence-Transformers model to bake it into the image
# This prevents downloading the ~90MB model every time you run the container
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy the rest of the application source code
COPY . .

# Set the entrypoint to the main pipeline CLI
ENTRYPOINT ["python", "main.py"]
# Use CMD for default arguments (can be overridden)
CMD ["--help"]
