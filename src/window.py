import tkinter
from tkinter import Menu, Tk, Canvas, Entry, Button, filedialog, Label, Frame, ttk, Checkbutton, BooleanVar, RIDGE, \
    BOTH, YES, font
from PIL import ImageTk, Image
from skimage.io import imread, imsave, imshow, show
from skimage.color import gray2rgb
from skimage.transform import resize, rescale, pyramid_expand
import keras
from keras.models import load_model
from whole_field_test import evaluate_whole_field, draw_boxes
import numpy as np
from create_individual_lettuce_train_data import fix_noise_vetcorised
from contours_test import create_quadrant_image
from size_calculator import calculate_sizes, create_for_contours
import matplotlib.pyplot as plt
from threading import Thread
import time
from construct_quadrant_file import create_quadrant_file
import os

os.environ[
    'KMP_DUPLICATE_LIB_OK'] = 'True'  # This prevents a crash from improperly loading a GPU library, but prevents using it I think. Comment out to see if it will work on your machine
from zipfile import ZipFile
import _thread
from tkinter import messagebox
from shutil import copy2


class LettuceApp(Tk):

    def __init__(self):
        Tk.__init__(self)

        self.width = 1200
        self.height = 900
        self.img_width = 0
        self.img_height = 0
        self.geometry(str(self.width) + "x" + str(self.height))
        self.title("AirSurf-Lettuce")
        self.info_image = ImageTk.PhotoImage(Image.fromarray(imread("info_icon.png")))

        self.input_frame = Frame(master=self)
        self.input_frame.config(width=self.width, height=30)

        self.file_frame = Frame(master=self.input_frame, borderwidth=2, relief=RIDGE, padx=15)
        self.file_frame.pack(side=tkinter.LEFT, fill=BOTH, expand=YES)

        self.gps_frame = Frame(master=self.input_frame, borderwidth=2, relief=RIDGE, padx=15, pady=2)
        self.gps_frame.pack(side=tkinter.LEFT, fill=BOTH, expand=YES)

        self.gps_label = Label(master=self.gps_frame, text="2. GPS", font=(font.BOLD, 20))
        self.gps_label.pack(side=tkinter.LEFT)

        self.gps_lat_frame = Frame(master=self.gps_frame)
        self.gps_lat_frame.pack(side=tkinter.TOP)

        self.gps_long_frame = Frame(master=self.gps_frame)
        self.gps_long_frame.pack(side=tkinter.TOP)

        self.config_frame = Frame(master=self.input_frame, borderwidth=2, relief=RIDGE, padx=15, pady=2)
        self.config_frame.pack(side=tkinter.LEFT, fill=BOTH, expand=YES)

        self.config_label = Label(master=self.config_frame, text="3. Configuration", font=(font.BOLD, 20))
        self.config_label.pack(side=tkinter.LEFT)

        self.config_rot_frame = Frame(master=self.config_frame)
        self.config_rot_frame.pack(side=tkinter.TOP)

        self.config_rot_info = Button(master=self.config_rot_frame, command=self.rot_info, image=self.info_image, bd=0)
        # self.config_rot_info.config(image=self.info_image)
        self.config_rot_info.pack(side=tkinter.RIGHT)

        self.config_preproc_frame = Frame(master=self.config_frame)
        self.config_preproc_frame.pack(side=tkinter.TOP)

        self.config_preproc_info = Button(master=self.config_preproc_frame, command=self.overflown_info,
                                          image=self.info_image, bd=0)
        self.config_preproc_info.pack(side=tkinter.RIGHT)

        self.start_button_frame = Frame(master=self.input_frame, borderwidth=2, relief=RIDGE, pady=15)
        self.start_button_frame.pack(side=tkinter.LEFT, fill=BOTH, expand=YES)

        # 52.437348, 0.379331, rotation=31.5
        self.in_long_label = Label(master=self.gps_long_frame, text="Longitude:")
        self.in_long_entry = Entry(master=self.gps_long_frame, text="52.437348", width=10)
        self.in_lat_label = Label(master=self.gps_lat_frame, text="Latitude:")
        self.in_lat_entry = Entry(master=self.gps_lat_frame, text="0.379331", width=10)

        self.in_rot_label = Label(master=self.config_rot_frame, text="Rotation:")
        self.in_rot_entry = Entry(master=self.config_rot_frame, text="31.5", width=5)

        self.in_long_label.pack(side=tkinter.LEFT)
        self.in_long_entry.pack(side=tkinter.LEFT, fill=BOTH, expand=YES)
        self.in_lat_label.pack(side=tkinter.LEFT)
        self.in_lat_entry.pack(side=tkinter.LEFT, fill=BOTH, expand=YES)

        self.in_rot_label.pack(side=tkinter.LEFT)
        self.in_rot_entry.pack(side=tkinter.LEFT)

        # Checkbox code
        self.overflow = BooleanVar()
        self.ndvi_check_label = Label(master=self.config_preproc_frame, text="Overflown NDVI")
        self.ndvi_check_label.pack(side=tkinter.LEFT)
        self.in_ndvi_check = Checkbutton(master=self.config_preproc_frame, onvalue=True, offvalue=False,
                                         variable=self.overflow)
        self.in_ndvi_check.pack(side=tkinter.LEFT)

        self.in_filename_label = Label(master=self.file_frame, text="1. Load Image:", font=(font.BOLD, 20))
        self.in_filename_entry = Entry(master=self.file_frame, textvariable="Input FileName", width=10)
        self.in_filename_browse = Button(master=self.file_frame, text="...", width=3, command=self.open_image)
        # self.in_filename_submit = Button(master=self.input_frame, text="Submit", width=10, command=self.load_image)

        self.in_filename_start = Button(master=self.start_button_frame, text="4. START", width=10, font=(font.BOLD, 20),
                                        command=self.run_pipeline_threaded)
        self.in_filename_label.pack(side=tkinter.LEFT)
        self.in_filename_entry.pack(side=tkinter.LEFT)
        self.in_filename_browse.pack(side=tkinter.LEFT)
        # self.in_filename_submit.pack(side=tkinter.LEFT)
        self.in_filename_start.pack()

        self.input_frame.pack(fill=BOTH, expand=YES)
        self.file_frame.pack()
        self.gps_frame.pack()
        self.config_frame.pack()

        self.output_frame = Frame(master=self.input_frame, pady=2, borderwidth=2, relief=RIDGE)
        self.output_frame.config(width=self.width, height=self.height - 30)

        self.out_filename_label = Label(master=self.output_frame, text="Output:")
        self.out_filename_entry = Entry(master=self.output_frame, textvariable="Output FileName")
        self.out_filename_browse = Button(master=self.output_frame, text="...", width=3, command=self.file_dialog)
        self.out_filename_save = Button(master=self.output_frame, text="Save", width=3, command=self.thread_save_output)
        self.out_filename_label.pack(side=tkinter.LEFT)
        self.out_filename_entry.pack(side=tkinter.LEFT)
        self.out_filename_browse.pack(side=tkinter.LEFT)
        self.out_filename_save.pack(side=tkinter.LEFT)
        self.output_frame.pack(side=tkinter.LEFT, fill=BOTH, expand=YES)

        # create tabs.
        self.tab_names = ["original", "normalised", "counts", "size distribution", "harvest regions"]
        self.tabControl = ttk.Notebook(self)
        self.tabs = {}
        self.canvas = {}
        self.photo = {}
        self.photo_config = {}
        self.src_image = None
        for tab_name in self.tab_names:
            tab = ttk.Frame(self.tabControl)
            self.tabControl.add(tab, text=tab_name)
            self.tabs[tab_name] = tab
            self.canvas[tab_name] = Canvas(tab, highlightthickness=0, highlightbackground="black", bd=0,
                                           bg="light gray")
            self.canvas[tab_name].config(width=self.width, height=self.height - 75)
            self.canvas[tab_name].pack()
            self.photo[tab_name] = None
            self.photo_config[tab_name] = None

        self.tabControl.pack(expand=len(self.tab_names), fill="both")

        # self.scrollable_canvas = ScrollCanvas(self, self, self.zoom_val)

        self.filename = None
        self.pipeline_thread = None
        self.name = None

    def rot_info(self):
        messagebox.showinfo("Rotation Information",
                            "The value you enter for rotation should be the value in degrees that your image is rotated counter-clockwise from north. If you had an arrow pointing north on the image, put the angle between the positive y-axis and the arrow, going counter-clockwise.")

    def overflown_info(self):
        messagebox.showinfo("Overflown NDVI Infomation",
                            "Check this box if your NDVI image was processed in such a way that the bright areas have overflown and appear dark.")

    def file_dialog(self):
        filename = filedialog.askdirectory(initialdir="./")
        self.out_filename_entry.delete(0, 'end')
        self.out_filename_entry.insert(0, filename)

    def thread_save_output(self):
        _thread.start_new_thread(self.save_output, ())

    def save_output(self):
        zipf = ZipFile(self.out_filename_entry.get() + "/" + self.name + '.zip', 'w')
        for root, dirs, files in os.walk("../data/" + self.name):
            for file in files:
                zipf.write(os.path.join(root, file))
        zipf.close()

        messagebox.showinfo("Saving Complete", message="All images zipped successfully")

    def open_image(self):
        filename = filedialog.askopenfilename(initialdir="./")
        self.in_filename_entry.delete(0, 'end')
        self.in_filename_entry.insert(0, filename)
        self.load_image()

    def load_image(self):
        self.filename = self.in_filename_entry.get()
        if os.path.isfile(self.filename):
            # load the image as a photo
            self.src_image = imread(self.filename).astype(np.uint8)
            self.img_width = self.src_image.shape[1]
            self.img_height = self.src_image.shape[0]
            # ensure its a rgb image.
            print(self.src_image.shape)
            if len(self.src_image.shape) == 2:
                self.src_image = gray2rgb(self.src_image)
            else:
                self.src_image = self.src_image[:, :, :3]
            self.draw_image(self.src_image, self.tab_names[0])

    def draw_image(self, img, tab_name):
        self.src_image = img
        self.photo[tab_name] = ImageTk.PhotoImage(Image.fromarray(img).resize((self.width, self.height)))

        # eitjer create an image on the canvas, or overwrite.
        if self.photo_config[tab_name] is None:
            self.photo_config[tab_name] = self.canvas[tab_name].create_image(0, 0, anchor=tkinter.NW,
                                                                             image=self.photo[tab_name])
        else:
            self.canvas[tab_name].itemconfig(self.photo_config[tab_name], image=self.photo[tab_name])

        # select the tab we're drawing too.
        self.tabControl.select(self.tab_names.index(tab_name))

    def run_pipeline_threaded(self):
        if self.pipeline_thread is None:
            self.pipeline_thread = Thread(target=self.run_pipeline)
            self.pipeline_thread.start()

    def run_pipeline(self):
        # extract long,lat,rot here.
        lat = float(self.in_lat_entry.get())
        long = float(self.in_long_entry.get())
        rot = float(self.in_rot_entry.get())

        # print(self.overflow.get())

        self.name = os.path.splitext(os.path.basename(self.filename))[0]
        print(os.path.splitext(os.path.basename(self.filename)))
        print(self.filename)
        output_dir = os.path.dirname(self.filename) + "/../data/" + self.name + "/"
        Image.MAX_IMAGE_PIXELS = None
        output_name = output_dir + "grey_conversion.png"
        print(output_name)

        # If the box is not checked, this will run and copy the file to the new location
        if not self.overflow.get():
            if not os.path.exists(output_name):
                if not os.path.exists("../data"):
                    os.mkdir("../data")

                if not os.path.exists("../data/" + self.name):
                    os.mkdir("../data/" + self.name)

                copy2(self.filename, output_name)

        if not os.path.exists(output_name):
            self.src_image = gray2rgb(self.src_image)
            img1 = fix_noise_vetcorised(self.src_image)

            # create dir.
            if not os.path.exists("../data"):
                os.mkdir("../data")

            if not os.path.exists("../data/" + self.name):
                os.mkdir("../data/" + self.name)

            imsave(output_name, img1)
        else:
            img1 = imread(output_name).astype(np.uint8)[:, :, :3]

        self.draw_image(img1, self.tab_names[1])
        time.sleep(2)

        print("Evaluating Field")
        keras.backend.clear_session()
        loaded_model = load_model('../model/trained_model_new2.h5')
        evaluate_whole_field(output_dir, img1, loaded_model)
        boxes = np.load(output_dir + "boxes.npy").astype("int")

        im = draw_boxes(gray2rgb(img1.copy()), boxes, color=(255, 0, 0))
        imsave(output_dir + "counts.png", im)
        self.draw_image(im, self.tab_names[2])
        time.sleep(2)

        print("Calculating Sizes")

        labels, size_labels = calculate_sizes(boxes, img1)
        label_ouput = np.array([size_labels[label] for label in labels])

        np.save(output_dir + "size_labels.npy", label_ouput)

        RGB_tuples = [[0, 0, 255], [0, 255, 0], [255, 0, 0]]
        color_field = create_for_contours(self.name, img1, boxes, labels, size_labels, RGB_tuples=RGB_tuples)

        imsave(output_dir + "sizes.png", color_field)
        self.draw_image(color_field, self.tab_names[3])
        time.sleep(2)

        # create quadrant harvest region image.
        output_field = create_quadrant_image(self.name, color_field)
        im = Image.fromarray(output_field.astype(np.uint8), mode="RGB")
        im = im.resize((self.width, self.height))
        im = np.array(im.getdata(), np.uint8).reshape(self.height, self.width, 3)

        imsave(output_dir + "harvest_regions.png", im)
        self.draw_image(im, self.tab_names[4])
        time.sleep(2)

        # make the csv file.
        create_quadrant_file(output_dir, self.name, self.img_height, self.img_width, boxes, label_ouput, lat, long,
                             rotation=rot, region_size=230)

        self.pipeline_thread = None

        messagebox.showinfo("Process Complete", message="Pipeline analysis has completed.")


def main():
    if not os.path.isdir("./data"):
        os.mkdir("./data")

    lettuce_app = LettuceApp()
    lettuce_app.mainloop()
    lettuce_app.quit()


if __name__ == "__main__":
    main()
