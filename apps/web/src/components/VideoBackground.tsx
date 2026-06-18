import { forwardRef, type VideoHTMLAttributes } from "react";

type VideoBackgroundProps = VideoHTMLAttributes<HTMLVideoElement> & {
  className?: string;
};

export const VideoBackground = forwardRef<HTMLVideoElement, VideoBackgroundProps>(
  ({ className, ...props }, ref) => (
    <video
      ref={ref}
      className={className ?? "absolute inset-0 h-full w-full object-contain"}
      autoPlay
      playsInline
      muted
      {...props}
    />
  ),
);

VideoBackground.displayName = "VideoBackground";
