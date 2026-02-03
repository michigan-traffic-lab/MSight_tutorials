from msight_vision.utils import ImageRetriever
from msight_vision import Yolo26Detector, HashLocalizer, SortTracker, ClassicWarper
from msight_vision.fuser import HungarianFuser
from msight_vision.state_estimator import FiniteDifferenceStateEstimator
from msight_base import Frame
from pathlib import Path
import pdb
import cv2
import torch
import time
from utils import plot_2d_detection_results, load_locmaps, is_number
import yaml
from msight_base.visualizer import Visualizer

config_path = Path("./config.yaml")

with open(config_path, "r") as f:
    config = yaml.safe_load(f)

### image directory###
img_dir = Path("./test-data")
img_retriever = ImageRetriever(img_dir=img_dir)

### device
device = "cuda" if torch.cuda.is_available() else "cpu"

### initialize detector
model_path = config["model_config"]["ckpt_path"]
confthre = config["model_config"]["confthre"]
nmsthre = config["model_config"]["nmsthre"]
class_agnostic_nms = config["model_config"]["class_agnostic_nms"]
end2end = config["model_config"].get("end2end", False)
detector = Yolo26Detector(model_path=Path(model_path), device=device, confthre=confthre, nmsthre=nmsthre, fp16=False, class_agnostic_nms=class_agnostic_nms, end2end=end2end)

### initialize localizer
loc_maps_path = config ["loc_maps"]
loc_maps = load_locmaps(loc_maps_path)
localizers = {key: HashLocalizer(lat_map=item['lat_map'], lon_map=item['lon_map']) for key, item in loc_maps.items()}

## initialize fuser
fuser = HungarianFuser(coverage_zones=config["fusion_config"]["coverage_zones"])

## initialize tracker
tracker = SortTracker(use_filtered_position=config["tracker_config"].get("use_filtered_position", False), output_predicted=config["tracker_config"].get("output_predicted", False))

## initialize state estimator
state_estimator = FiniteDifferenceStateEstimator()

## initialize visualizer
visualizer = Visualizer("./viz/mcity.png")

step = 0
while True:
    img_buff = img_retriever.get_image()
    if img_buff is None:
        break
    
    print(f"\n[Step {step:05d}]")

    ## detection
    t0 = time.perf_counter()
    detection_buffer = {}
    for sensor_name in img_buff.keys():
        img = img_buff[sensor_name]["image"]
        result = detector.detect(img, img_buff[sensor_name]["timestamp"], "fisheye")
        detection_buffer[sensor_name] = result
        # print(sensor_name, result.object_list)
    print(f"  Detection:        {(time.perf_counter() - t0) * 1000:.2f} ms")
    
    ## localization
    t0 = time.perf_counter()
    for sensor_name, detection_result in detection_buffer.items():
        localizer = localizers[sensor_name]
        localizer.localize(detection_result)

    ## remove those objects that are not localized (obj.lat isn't a number like None, inf, -inf)
    for sensor_name, detection_result in detection_buffer.items():
        detection_result.object_list = [obj for obj in detection_result.object_list if is_number(obj.lat) and is_number(obj.lon)]
    print(f"  Localization:     {(time.perf_counter() - t0) * 1000:.2f} ms")

    ## fusion
    t0 = time.perf_counter()
    fusion_result = fuser.fuse(detection_buffer)
    print(f"  Fusion:           {(time.perf_counter() - t0) * 1000:.2f} ms")
    # pdb.set_trace()
    ## tracking
    t0 = time.perf_counter()
    tracking_result = tracker.track(fusion_result)
    print(f"  Tracking:         {(time.perf_counter() - t0) * 1000:.2f} ms")

    ## state estimation
    t0 = time.perf_counter()
    result = state_estimator.estimate(tracking_result)
    print(f"  State Estimation: {(time.perf_counter() - t0) * 1000:.2f} ms")

    ## visualization
    t0 = time.perf_counter()
    # creating frame
    result_frame = Frame(step)
    for obj in result:
        result_frame.add_object(obj)
    vis_img = visualizer.render(result_frame , with_traj=True)
    key = cv2.waitKey(1)
    detection2d_results_img = plot_2d_detection_results(img_buff, detection_buffer, grid_size=(2, 1), size=(640, 960))
    # put vis_img and detection2d_results_img side by side, by checking their heights first
    if vis_img.shape[0] != detection2d_results_img.shape[0]:
        # resize detection2d_results_img to have the same height as vis_img, preserving aspect ratio
        scale = vis_img.shape[0] / detection2d_results_img.shape[0]
        new_width = int(detection2d_results_img.shape[1] * scale)
        new_height = vis_img.shape[0]
        detection2d_results_img = cv2.resize(detection2d_results_img, (new_width, new_height))
    combined_img = cv2.hconcat([vis_img, detection2d_results_img])
    cv2.imshow("Combined Results", combined_img)
    cv2.waitKey(1)  # refresh display
    
    print(f"  Visualization:    {(time.perf_counter() - t0) * 1000:.2f} ms")

    step += 1

cv2.destroyAllWindows() 
