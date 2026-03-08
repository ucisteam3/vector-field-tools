/** Export settings matching backend ClipExporter / settings_manager */

export type ExportMode = "landscape_fit" | "face_tracking";

export type ExportSettings = {
  export_mode: ExportMode;
  dynamic_zoom_enabled: boolean;
  video_flip_enabled: boolean;
  audio_pitch_enabled: boolean;

  subtitle_enabled: boolean;
  subtitle_font: string;
  subtitle_fontsize: number;
  subtitle_text_color: string;
  subtitle_outline_color: string;
  subtitle_outline_width?: number;
  subtitle_highlight_color: string;
  subtitle_position_y: number;

  watermark_enabled: boolean;
  watermark_type: "text" | "image";
  watermark_text: string;
  watermark_font: string;
  watermark_size: number;
  watermark_opacity: number;
  watermark_pos_x: number;
  watermark_pos_y: number;
  watermark_image_path: string;
  watermark_image_scale?: number;
  watermark_image_opacity?: number;
  watermark_outline_width?: number;
  watermark_outline_color?: string;

  bgm_enabled: boolean;
  bgm_file_path: string;
};

export const DEFAULT_EXPORT_SETTINGS: ExportSettings = {
  export_mode: "face_tracking",
  dynamic_zoom_enabled: false,
  video_flip_enabled: false,
  audio_pitch_enabled: false,

  subtitle_enabled: false,
  subtitle_font: "Arial",
  subtitle_fontsize: 24,
  subtitle_text_color: "#FFFFFF",
  subtitle_outline_color: "#000000",
  subtitle_outline_width: 2,
  subtitle_highlight_color: "#FFFF00",
  subtitle_position_y: 50,

  watermark_enabled: false,
  watermark_type: "text",
  watermark_text: "Watermark",
  watermark_font: "Arial",
  watermark_size: 48,
  watermark_opacity: 80,
  watermark_pos_x: 50,
  watermark_pos_y: 50,
  watermark_image_path: "",
  watermark_image_scale: 50,
  watermark_image_opacity: 100,
  watermark_outline_width: 2,
  watermark_outline_color: "#000000",

  bgm_enabled: false,
  bgm_file_path: "",
};

export const EXPORT_MODE_OPTIONS: { value: ExportMode; label: string }[] = [
  { value: "face_tracking", label: "9:16 Portrait (Shorts/Reels)" },
  { value: "landscape_fit", label: "Landscape (Blur Background)" },
];
