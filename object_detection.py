import time
import cv2
import numpy as np

class ObjectDetection:
    def __init__(self):
        self.MODEL = cv2.dnn.readNet(
            'models/yolov4.weights',
            'models/yolov4.cfg'
        )

        self.CLASSES = []
        with open("models/coco.names", "r") as f:
            self.CLASSES = [line.strip() for line in f.readlines()]

        self.OUTPUT_LAYERS = [self.MODEL.getLayerNames()[i - 1] for i in self.MODEL.getUnconnectedOutLayers()]
        np.random.seed(42)
        self.COLORS = np.random.randint(0, 255, size=(len(self.CLASSES), 3), dtype="uint8")

    def detectObj(self, snap):
        height, width, channels = snap.shape
        blob = cv2.dnn.blobFromImage(snap, 1/255, (256, 256), swapRB=True, crop=False)

        self.MODEL.setInput(blob)
        outs = self.MODEL.forward(self.OUTPUT_LAYERS)

        # Showing informations on the screen
        class_ids = []
        confidences = []
        boxes = []
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:
                    # Object detected
                    center_x = int(detection[0]*width)
                    center_y = int(detection[1]*height)
                    w = int(detection[2]*width)
                    h = int(detection[3]*height)

                    # Rectangle coordinates
                    x = int(center_x - w/2)
                    y = int(center_y - h/2)

                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        font = cv2.FONT_HERSHEY_PLAIN
        for i in range(len(boxes)):
            if i in indexes:
                x, y, w, h = boxes[i]
                label = str(self.CLASSES[class_ids[i]])
                percentage = "{:.2f}%".format(confidences[0] * 100)
                # color = self.COLORS[i]
                color = [int(c) for c in self.COLORS[class_ids[i]]]
                cv2.rectangle(snap, (x, y), (x + w, y + h), color, 2)
                cv2.putText(snap, label, (x, y - 5), font, 2, color, 2)
                cv2.putText(snap, percentage, (x, y - 25), font, 2, color, 2)

        try: 
            # Return labels
            ObjectDetection.lbl = label
        except:
            ObjectDetection.lbl = "No label"
        return snap

class VideoStreaming(object):
    def __init__(self):
        super(VideoStreaming, self).__init__()
        self.VIDEO = cv2.VideoCapture(0)
        self.MODEL = ObjectDetection()
        self._preview = True
        self._detect = False

    @property
    def preview(self):
        return self._preview

    @preview.setter
    def preview(self, value):
        self._preview = bool(value)

    @property
    def detect(self):
        return self._detect

    @detect.setter
    def detect(self, value):
        self._detect = bool(value)

    def show(self):
        while(self.VIDEO.isOpened()):
            ret, snap = self.VIDEO.read()
            
            if ret == True:
                if self._preview:
                    if self.detect:
                        snap = self.MODEL.detectObj(snap)
                        try:
                            VideoStreaming.lblret = self.MODEL.lbl
                        except:
                            pass

                else:
                    snap = np.zeros((
                        int(self.VIDEO.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                        int(self.VIDEO.get(cv2.CAP_PROP_FRAME_WIDTH))
                    ), np.uint8)
                    label = 'camera disabled'
                    H, W = snap.shape
                    font = cv2.FONT_HERSHEY_PLAIN
                    color = (255,255,255)
                    cv2.putText(snap, label, (W//2 - 100, H//2), font, 2, color, 2)
                
                frame = cv2.imencode('.jpg', snap)[1].tobytes()
                yield (b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.01)

            else:
                break
        print('off')
