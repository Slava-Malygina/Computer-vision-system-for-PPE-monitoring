from modules.video_processor import VideoProcessor
from modules.logger import ViolationLogger

if __name__ == "__main__":
    video_path = r"../videos/example_3.mp4"
    model_path = r"../model/ppe_best_3.pt"
    output_video_path = r"../videos/example3_out2.mp4"

    process_every_nth_frame = 5

    logger = ViolationLogger(max_buffer_size=50)
    processor = VideoProcessor(
        model_path=model_path,
        logger=logger,
        save_frames=True,
        output_video_path=output_video_path
    )

    processor.process_video(
        video_path=video_path,
        process_every_nth_frame=process_every_nth_frame
    )

    logger.flush()
    stats = logger.get_log_stats()

    print("Лог сохранен:", logger.get_file_path())
