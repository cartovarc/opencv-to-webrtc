import time, sys
from rtp_pipeline import RtpPipeline

if __name__ == '__main__':
    args = sys.argv
    stream_name = args[1]
    rtp_pipeline_handler = RtpPipeline(stream_name)
    rtp_pipeline_handler.startStreaming()

    while rtp_pipeline_handler.running:
        print("streaming...")
        time.sleep(1)
