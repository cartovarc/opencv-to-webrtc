import cv2, gi, json, requests, threading, time

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib
GObject.threads_init()
Gst.init(None)


class RtpPipeline(object):
    def __init__(self, stream_name):
        self.stream_name = stream_name
        self.number_frames = 0
        self.cap = cv2.VideoCapture(0)
        self.w = 640 # self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.h = 360 # self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print("w %s h %s"%(self.w, self.h))
        self.fps = 24 #self.cap.get(cv2.CV_CAP_PROP_FPS)
        self.duration = 1 / self.fps * Gst.SECOND  # duration of a frame in nanoseconds
        self.running = False  # false when not clients

    def startStreaming(self):
        self.running = True
        thread = threading.Thread(target=self.push_to_pipeline, args=[])
        thread.daemon = True
        thread.start()

    def push_to_pipeline(self):
        try:
            r = requests.post(url="http://127.0.0.1:4001/create/%s" % self.stream_name, timeout=1)
            content = r.content
            print(content)
            res = json.loads(content.decode("utf-8"))
            rtp_port = res["rtp_port"]
            print("assigned rtp port %s" % rtp_port)
        except requests.exceptions.RequestException:
            print("Error vinculando rtp con con webrtc - Revisar modulo rtmp-to-webrtc")
            return

        if rtp_port is None:
            self.running = False
            print("Error intentando obtener un puerto rtp")
            return

        launch_string = 'appsrc name=source is-live=true format=GST_FORMAT_TIME ' \
                        ' caps=video/x-raw,format=BGR,width=%s,height=%s,framerate=%s/1 ' \
                        '! videoconvert ! video/x-raw,format=I420 ' \
                        '! x264enc speed-preset=ultrafast tune=zerolatency byte-stream=true ' \
                        '! h264parse ! rtph264pay config-interval=-1 pt=96 ! udpsink host=127.0.0.1 port=%s sync=false' % (
                        self.w, self.h, self.fps, rtp_port)

        pipeline = Gst.parse_launch(launch_string)
        appsrc = pipeline.get_child_by_name('source')
        pipeline.set_state(Gst.State.PLAYING)

        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    time.sleep(0.5)
                    continue
                frame = cv2.resize(frame, (self.w, self.h), interpolation=cv2.INTER_AREA) # resized frame
                cv2.putText(frame,'HELLO WORLD',(100,100), cv2.FONT_HERSHEY_SIMPLEX, 1,(255,0,0),2)
		#cv2.imshow("TEST", frame)
                data = frame.tostring()
                buf = Gst.Buffer.new_allocate(None, len(data), None)
                buf.fill(0, data)
                buf.duration = self.duration
                timestamp = self.number_frames * self.duration
                buf.pts = buf.dts = int(timestamp)
                buf.offset = timestamp
                self.number_frames += 1
                retval = appsrc.emit('push-buffer', buf)
                if retval != Gst.FlowReturn.OK:
                    print(retval)
                k = cv2.waitKey(33)
                if k==27:    # Esc key to stop
                    break
                time.sleep(1/self.fps)
            except Exception:
                break
        pipeline.set_state(Gst.State.NULL)
