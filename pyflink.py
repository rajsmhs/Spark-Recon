from pyflink.datastream import StreamExecutionEnvironment, CheckpointingMode, RuntimeExecutionMode
from pyflink.configuration import Configuration
import os

def create_flink_job():
    # Create configuration
    config = Configuration()
    
    # AWS credentials and S3 configuration
    aws_configs = {
        "fs.s3a.access.key": os.getenv('AWS_ACCESS_KEY_ID'),
        "fs.s3a.secret.key": os.getenv('AWS_SECRET_ACCESS_KEY'),
        "fs.s3a.endpoint": "s3.amazonaws.com",
        "fs.s3a.path.style.access": "true",
        "fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
        "fs.s3.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
        "fs.s3a.aws.credentials.provider": "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
        # Add these configurations
        "fs.s3a.connection.maximum": "100",
        "fs.s3a.connection.timeout": "10000",
        "fs.s3a.connection.establish.timeout": "5000",
        "fs.s3a.attempts.maximum": "20",
        "state.backend": "filesystem",
        "state.checkpoints.dir": "s3://your-bucket/checkpoints",
        "execution.checkpointing.interval": "10000",
        "execution.checkpointing.mode": "EXACTLY_ONCE",
        "execution.checkpointing.timeout": "600000",
        "execution.checkpointing.max-concurrent-checkpoints": "1",
        "execution.checkpointing.min-pause": "500",
        "execution.checkpointing.externalized-checkpoint-retention": "RETAIN_ON_CANCELLATION"
    }

    # Apply configurations
    for key, value in aws_configs.items():
        config.set_string(key, value)

    # Create execution environment
    env = StreamExecutionEnvironment.get_execution_environment(config)

    # Set runtime mode to STREAMING
    env.set_runtime_mode(RuntimeExecutionMode.STREAMING)

    # Configure checkpointing
    env.enable_checkpointing(10000)  # 10 seconds
    checkpoint_config = env.get_checkpoint_config()
    checkpoint_config.set_checkpoint_mode(CheckpointingMode.EXACTLY_ONCE)
    checkpoint_config.set_checkpoint_timeout(600000)  # 10 minutes
    checkpoint_config.set_max_concurrent_checkpoints(1)
    checkpoint_config.set_min_pause_between_checkpoints(500)
    checkpoint_config.enable_externalized_checkpoints(
        env.get_checkpoint_config().ExternalizedCheckpointCleanup.RETAIN_ON_CANCELLATION
    )
    checkpoint_config.set_checkpoint_storage("s3://your-bucket/checkpoints")

    return env

def create_source_and_process(env):
    # Your source and processing logic here
    # Example:
    source = ...  # Your source configuration
    
    # Add a print statement to verify data flow
    source.map(lambda x: print(f"Processing record: {x}")).name("print_operator")
    
    return source

if __name__ == '__main__':
    try:
        # Create the Flink job
        env = create_flink_job()
        
        # Create source and processing
        datastream = create_source_and_process(env)
        
        # Print the execution plan
        print("Execution Plan:")
        print(env.get_execution_plan())
        
        # Execute the job
        print("Starting Flink job...")
        env.execute("Flink Job with S3 Checkpointing")
        
    except Exception as e:
        print(f"Error executing Flink job: {str(e)}")
        raise
