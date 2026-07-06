# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install uv for fast dependency management
RUN pip install uv

# Set the working directory in the container
WORKDIR /app

# Copy the dependency files
COPY pyproject.toml uv.lock ./

# Install the dependencies using uv
RUN uv sync --frozen

# Copy the rest of the application code
COPY . .

# Create directories for runtime data
RUN mkdir -p data faiss_index templates static

# Expose port 8000
EXPOSE 8000

# Command to run the application using uv and uvicorn
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
