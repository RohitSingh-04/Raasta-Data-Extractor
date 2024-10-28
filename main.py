from tkinter import *
from tkinter import filedialog, messagebox, ttk  # Import for the progress bar
from threading import Thread
from dataHunter import DataHunter
from tkinter import Tk, Label
from PIL import Image, ImageTk

def set_file_name(filename):
    try:
        FileLabel_Text.config(text=filename)
        text_canvas.update_idletasks()
        text_canvas.config(scrollregion=text_canvas.bbox("all"))
    except NameError:
        ...


class AnimatedGif:
    def __init__(self, master, gif_path, delay=100, size=(250, 200), pady = 10, bg = "white"):
        self.master = master
        self.delay = delay  # Time between frames in milliseconds
        self.size = size  # Desired size for the frames

        # Load the GIF file
        self.frames = []
        gif = Image.open(gif_path)

        # Extract frames, resize them, and store as ImageTk.PhotoImage objects
        try:
            while True:
                frame = gif.copy()  # Copy the frame to avoid altering the original
                frame = frame.resize(self.size)  # Resize the frame
                self.frames.append(ImageTk.PhotoImage(frame))
                gif.seek(len(self.frames))  # Move to the next frame
        except EOFError:
            pass  # End of the GIF

        # Set up label widget to display the GIF frames
        self.label = Label(master)
        self.label.pack()
        
        # Start the animation
        self.current_frame = 0
        self.update_animation()  

    def update_animation(self):
        # Display the current frame
        self.label.config(image=self.frames[self.current_frame])
        self.current_frame = (self.current_frame + 1) % len(self.frames)  # Loop the frames
        self.master.after(self.delay, self.update_animation)  # Schedule the next frame update
    def delete(self):
        self.label.pack_forget()
        del self

class ModFrame(Frame):
    def __init__(self, framename,   *args, **kwargs):
        super().__init__(*args, **kwargs)
        Label(text=framename,  bg = "white").pack()

class ModButton(Button):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class RaastaApp(Tk):
    def __init__(self, screenName: str | None = None, baseName: str | None = None, className: str = "Tk", useTk: bool = True, sync: bool = False, use: str | None = None) -> None:
        super().__init__(screenName, baseName, className, useTk, sync, use)
        self.gif = None
        
    
    def set_configurations(self):
        self.title("Raasta Data Extraction")
        self.geometry("800x500+0+0")
        self.resizable(False, False)

    def create_required_frames(self):
        self.TopFrame = Frame(self, bg= "white")
        self.MidFrame = Frame(self, bg= "white")
        self.BottomFrame = Frame(self, bg= "white")

        self.Frame_Status = Frame(self.BottomFrame, bg= "white")
        self.Frame_Buttons = Frame(self.BottomFrame, bg= "white")

        # Progress bar
        self.progress = ttk.Progressbar(
            self.Frame_Status, orient="horizontal", length=400, mode="determinate"
        )
        self.progress["value"] = 0
        self.progress["maximum"] = 3  # Three main steps

        # Save As button (initially hidden)
        self.save_button = ModButton(self.Frame_Buttons, text="Save as", command=self.save_as, bg="white")
        self.save_button.pack(side="bottom")
        self.save_button.pack_forget()  # Hide initially

    def pack_items(self):
        self.TopFrame.pack(pady=(0, 10), side="top", fill="x")
        self.MidFrame.pack(anchor="nw", side="top", fill="x")

    def pack_bottom_frame(self):
        self.BottomFrame.pack(side="top", fill="both", pady=10)
        self.Frame_Status.pack(anchor="center", pady=10)
        self.Frame_Buttons.pack(side="top", fill="both", pady=(10, 20))

    def selectFile(self):
        file = filedialog.askopenfile(defaultextension='.csv', filetypes=[("CSV Files", "*.csv")])
        if file:
            set_file_name(file.name)
            self.pack_bottom_frame()
            self.progress['value'] = 0
            self.progress.pack(pady=5)  # Pack progress bar only after a file is selected
            self.update_idletasks()  # Update the UI to show the new status frame

            # Run the tasks in a separate thread
            self.thread = Thread(target=self.run_data_hunter, args=(file,), daemon=True)
            self.thread.start()

    def run_data_hunter(self, file):
        try:
            MyHunter = DataHunter(file.name)

            # Step 1: Run downloadPDFs
            self.update_status("Downloading PDFs...", step=1)
            for message in MyHunter.downloadPDFs():
                self.update_status(message)

            # Step 2: Extract text from PDFs
            self.update_status("Extracting text from PDFs...", step=2)
            text_extraction_message = MyHunter.get_pdf_text()
            self.update_status(text_extraction_message)

            # Step 3: Generate data from PDFs
            self.update_status("Generating data from PDFs...", step=2.5)
            for message in MyHunter.get_data_from_pdf(MyHunter.new_datas):
                self.update_status(message)

            # Completion message and show "Save As" button
            self.update_status("Data extraction completed successfully.", step=3, complete=True)
            self.save_button.pack(side="bottom")  # Show the "Save As" button

        except Exception as e:
            self.update_status(f"Error: {e}")

    def save_as(self):
        file_saveas = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[["CSV File", ".csv"]])
        if file_saveas:
            from shutil import move
            move("main.csv", file_saveas)
            messagebox.showinfo("Done!", "Saved the File!")
        
    def update_status(self, message, step=0, complete=False):
        # Update the status label with the new message
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)
            if self.gif:
                self.gif.delete()

            if "download" in message.lower():
                self.gif = AnimatedGif(self.Frame_Status, "gifs/download.gif", delay=100)
            
            elif "think" in message.lower():
                self.gif = AnimatedGif(self.Frame_Status, "gifs/ai-gpt.gif", delay=100, bg="white")
            
            elif "pdf" in message.lower():
                self.gif = AnimatedGif(self.Frame_Status, "gifs/ai-1.gif", delay=100, bg="white")

            else:
                self.gif = AnimatedGif(self.Frame_Status, "gifs/done.gif", delay=100, bg="white")
        else:
            self.status_label = Label(self.Frame_Status, text=message, bg="white")
            self.status_label.pack()

        # Update progress bar
        if step > 0:
            self.progress["value"] = step
        if complete:
            self.progress["value"] = 3
            self.progress.update_idletasks()  # Ensure UI reflects final state immediately


if __name__ == "__main__":
    root = RaastaApp("Raasta Data Extraction")

    root.set_configurations()
    root.create_required_frames()
    root.pack_items()
    root.configure(bg= "white")
    Label(root.TopFrame, text="Data Extractor", font="Calibri 18", bg="white").pack()

    SELECT_FILE_IMG = PhotoImage(file="imgs/file_select_icon.png")

    select_file_button = Button(root.MidFrame, image=SELECT_FILE_IMG, borderwidth=0, command=root.selectFile, bg= "white")
    select_file_button.pack(side="left", anchor="nw", padx=(40, 0))

    # Frame to contain canvas and scrollbar
    text_frame = Frame(root.MidFrame, background="white")
    text_frame.pack(side="left", fill="both", expand=True, padx=(4, 40))

    # Canvas for scrollable text
    text_canvas = Canvas(text_frame, background="white", height=30)
    text_canvas.pack(side="top", fill="x", expand=True)

    # File label inside canvas
    FileLabel_Text = Label(text_canvas, background="white", font="Calibri 14", fg="grey")
    text_canvas.create_window((0, 0), window=FileLabel_Text, anchor="w")

    # Thin horizontal scrollbar
    scroll_bar = Scrollbar(text_frame, orient="horizontal", command=text_canvas.xview, width=8)
    scroll_bar.pack(side="top", fill="x")
    text_canvas.config(xscrollcommand=scroll_bar.set)

    set_file_name("please select a file to continue")

    root.mainloop()
