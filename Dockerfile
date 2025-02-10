FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies
RUN yum install -y postgresql-devel

# Copy requirements file
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy function code
COPY src/etl_job.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "etl_job.lambda_handler" ]