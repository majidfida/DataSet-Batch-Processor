import os
from modules import utils, filter_crop, tiling, other_tasks
import gradio as gr
from modules.caption_manager import load_captions, save_caption

def save_caption_callback(caption):
    updated_captions = save_caption(caption)
    # Ensure an empty string is always in the list so user can clear
    if "" not in updated_captions:
        updated_captions.insert(0, "")
    # Return an update so the dropdown choices refresh and the current value remains the same
    return gr.update(choices=updated_captions, value=caption)

def build_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# DataSet Batch Processor")
        with gr.Tabs():
            # TAB 1: Tiling with Sub-Tabs
            with gr.Tab("Tiling"):
                with gr.Tabs():
                    # Sub-Tab A: Prepare Images for Tiling
                    with gr.Tab("Prepare Images for Tiling"):
                        gr.Markdown("**Filter & Auto-Crop**")
                        with gr.Row():
                            folder_input = gr.Textbox(label="Input Folder")
                            incompatible_path_input = gr.Textbox(label="Incompatible Folder")
                            cropped_path_input = gr.Textbox(label="Cropped Folder (must be empty)")
                        with gr.Row():
                            tile_size_input = gr.Number(value=1024, label="Tile Size (pixels)")
                            overlap_ratio_input = gr.Slider(0, 1, value=0.5, step=0.1, label="Overlap Ratio")
                            padding_input = gr.Number(value=10, label="Padding (pixels)")
                        filter_btn = gr.Button("Filter Incompatible")
                        auto_crop_btn = gr.Button("Auto Crop")
                        prep_status = gr.Textbox(label="Status", interactive=False)
                        stop_prep_btn = gr.Button("Stop")
                        filter_btn.click(
                            filter_crop.on_filter_incompatible,
                            inputs=[folder_input, incompatible_path_input, tile_size_input, overlap_ratio_input, padding_input],
                            outputs=prep_status
                        )
                        auto_crop_btn.click(
                            filter_crop.on_auto_crop,
                            inputs=[incompatible_path_input, cropped_path_input, tile_size_input, overlap_ratio_input, padding_input],
                            outputs=prep_status
                        )
                        stop_prep_btn.click(utils.stop_process, outputs=prep_status)
                        gr.Markdown("""
                        **Steps:**  
                        1. Click **Filter Incompatible** to move images that would produce partial tiles into the **Incompatible Folder**.  
                           A text file with recommended crop dimensions is created for each moved image.
                        2. Optionally, click **Auto Crop** to center-crop those images (adjusting the original dimensions so that slicing produces perfect 1:1 tiles) and save them in the **Cropped Folder**.
                        3. If auto-cropping removes important areas, use the recommended dimensions in the text file to crop manually.
                        4. Once your images are prepared (either remaining in the Input Folder or from the Cropped Folder), proceed to the **Tile Images** tab.
                        """)
                    # Sub-Tab B: Tile Images
                    with gr.Tab("Tile Images"):
                        gr.Markdown("**Perform the Actual Tiling**")
                        with gr.Row():
                            tile_input_folder = gr.Textbox(label="Input Folder (for Tiling)")
                            tile_output_folder = gr.Textbox(label="Tiled Output Folder (must be empty)")
                        with gr.Row():
                            tile_size_input2 = gr.Number(value=1024, label="Tile Size (pixels)")
                            overlap_ratio_input2 = gr.Slider(0, 1, value=0.5, step=0.1, label="Overlap Ratio")
                            padding_input2 = gr.Number(value=10, label="Padding (pixels)")
                            num_tiles_input = gr.Number(value=0, label="Number of Tiles (0 = Use Tile Size)")
                        with gr.Row():
                            pad_option_dropdown = gr.Dropdown(
                                choices=["None", "Extend Edges", "Auto Adjust", "Pad to Square"],
                                value="None",
                                label="Pad Option"
                            )
                        with gr.Row():
                            caption_dropdown = gr.Dropdown(
                                choices=load_captions(),
                                value="",
                                label="Manual Caption (Optional)",
                                allow_custom_value=True
                            )
                            save_caption_btn = gr.Button("Save Caption")
                        output_format_input = gr.Radio(choices=["None", "JPG", "PNG"],
                                                       value="None",
                                                       label="Output Image Format")
                        tile_btn = gr.Button("Process Images")
                        tile_stop_btn = gr.Button("Stop")
                        tile_status = gr.Textbox(label="Status", interactive=False)
                        tile_gallery = gr.Gallery(label="Tiled Images", show_label=False, height=400)
                        zip_btn = gr.Button("Download Processed Tiles")
                        zip_output = gr.File(label="ZIP File")
                        tile_btn.click(
                            tiling.on_tiling,
                            inputs=[tile_input_folder, tile_size_input2, overlap_ratio_input2, padding_input2,
                                    num_tiles_input, caption_dropdown, tile_output_folder,
                                    output_format_input, pad_option_dropdown],
                            outputs=[tile_status, tile_gallery]
                        )
                        tile_stop_btn.click(utils.stop_process, outputs=tile_status)
                        zip_btn.click(tiling.create_zip, inputs=tile_output_folder, outputs=zip_output)
                        save_caption_btn.click(save_caption_callback, inputs=caption_dropdown, outputs=caption_dropdown)
            # TAB 2: Merge Text Files
            with gr.Tab("Merge Text Files"):
                with gr.Row():
                    in_merge = gr.Textbox(label="Input Folder (with .txt files)")
                    out_merge = gr.Textbox(label="Output Folder (must be empty)")
                merge_btn = gr.Button("Process")
                stop_merge_btn = gr.Button("Stop")
                merge_output = gr.Textbox(label="Status", interactive=False)
                merge_btn.click(other_tasks.merge_text_files, inputs=[in_merge, out_merge], outputs=merge_output)
                stop_merge_btn.click(utils.stop_process, outputs=merge_output)
            # TAB 3: Image Format Converter
            with gr.Tab("Image Format Converter"):
                with gr.Row():
                    in_conv = gr.Textbox(label="Input Folder")
                    out_conv = gr.Textbox(label="Output Folder (must be empty)")
                with gr.Row():
                    old_format_dropdown = gr.Dropdown(choices=["jpg", "png", "bmp", "tiff", "gif", "webp", "heic", "cr2", "nef", "arw", "dng"],
                                                      label="Input Format", value="jpg")
                    new_format_dropdown = gr.Dropdown(choices=["jpg", "png", "bmp", "tiff", "gif", "webp"],
                                                      label="Output Format", value="jpg")
                jpg_quality_slider = gr.Slider(minimum=1, maximum=100, value=85, label="JPEG Quality", visible=True)
                png_compression_slider = gr.Slider(minimum=0, maximum=9, value=6, label="PNG Compression Level", visible=False)
                conv_btn = gr.Button("Process")
                stop_conv_btn = gr.Button("Stop")
                conv_output = gr.Textbox(label="Status", interactive=False)
                new_format_dropdown.change(other_tasks.update_conversion_settings, inputs=new_format_dropdown,
                                           outputs=[jpg_quality_slider, png_compression_slider])
                conv_btn.click(other_tasks.convert_images, inputs=[in_conv, out_conv, old_format_dropdown, new_format_dropdown,
                                                                    jpg_quality_slider, png_compression_slider],
                                outputs=conv_output)
                stop_conv_btn.click(utils.stop_process, outputs=conv_output)
            # TAB 4: Split JSONL File
            with gr.Tab("Split JSONL File"):
                with gr.Row():
                    in_jsonl = gr.Textbox(label="Input JSONL File")
                    out_jsonl = gr.Textbox(label="Output Folder (must be empty)")
                lines_jsonl = gr.Textbox(label="Number of lines per file", value="100")
                jsonl_btn = gr.Button("Process")
                stop_jsonl_btn = gr.Button("Stop")
                jsonl_output = gr.Textbox(label="Status", interactive=False)
                jsonl_btn.click(other_tasks.split_jsonl, inputs=[in_jsonl, out_jsonl, lines_jsonl], outputs=jsonl_output)
                stop_jsonl_btn.click(utils.stop_process, outputs=jsonl_output)
            # TAB 5: Remove Duplicates From Text File
            with gr.Tab("Remove Duplicates"):
                with gr.Row():
                    in_dup = gr.Textbox(label="Input File (with .txt files)")
                    out_dup = gr.Textbox(label="Output Folder (must be empty)")
                dup_btn = gr.Button("Process")
                stop_dup_btn = gr.Button("Stop")
                dup_output = gr.Textbox(label="Status", interactive=False)
                dup_btn.click(other_tasks.remove_duplicates, inputs=[in_dup, out_dup], outputs=dup_output)
                stop_dup_btn.click(utils.stop_process, outputs=dup_output)
            # TAB 6: Split Large Text File
            with gr.Tab("Split Large Text File"):
                with gr.Row():
                    in_split = gr.Textbox(label="Input Text File")
                    out_split = gr.Textbox(label="Output Folder (must be empty)")
                lines_split = gr.Textbox(label="Number of lines per file", value="100")
                split_btn = gr.Button("Process")
                stop_split_btn = gr.Button("Stop")
                split_output = gr.Textbox(label="Status", interactive=False)
                split_btn.click(other_tasks.split_large_text, inputs=[in_split, out_split, lines_split], outputs=split_output)
                stop_split_btn.click(utils.stop_process, outputs=split_output)
        gr.Markdown("""
        ---
        **Disclaimer:** Use at your own risk; always keep backups.
        **Credits:** Eagle-42
        """)
    return demo

if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="127.0.0.1", server_port=7868, inbrowser=True, allowed_paths=[os.getcwd()])
