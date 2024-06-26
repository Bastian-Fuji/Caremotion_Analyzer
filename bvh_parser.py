import numpy as np

class BVHNode:
    def __init__(self, name):
        self.name = name
        self.offset = np.zeros(3)
        self.channels = []
        self.children = []
        self.channel_values = []

    def add_child(self, child):
        self.children.append(child)

class BVHParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.root = None
        self.frames = []
        self.frame_time = 0

    def parse(self):
        with open(self.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        stack = []
        current_node = None
        reading_motion = False

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("HIERARCHY"):
                continue
            elif line.startswith("ROOT") or line.startswith("JOINT"):
                name = line.split()[1]
                node = BVHNode(name)
                if current_node is not None:
                    current_node.add_child(node)
                else:
                    self.root = node
                stack.append(node)
                current_node = node
            elif line.startswith("End Site"):
                node = BVHNode("End Site")
                current_node.add_child(node)
                stack.append(node)
                current_node = node
            elif line.startswith("OFFSET"):
                current_node.offset = np.array(list(map(float, line.split()[1:])))
            elif line.startswith("CHANNELS"):
                current_node.channels = line.split()[2:]
            elif line.startswith("}"):
                stack.pop()
                if stack:
                    current_node = stack[-1]
            elif line.startswith("MOTION"):
                reading_motion = True
            elif reading_motion:
                if line.startswith("Frames:"):
                    num_frames = int(line.split(':')[1].strip())
                elif line.startswith("Frame Time:"):
                    self.frame_time = float(line.split(':')[1].strip())
                else:
                    self.frames.append(list(map(float, line.split())))

        for frame in self.frames:
            self._assign_channel_values(self.root, frame)

    def _assign_channel_values(self, node, frame):
        num_channels = len(node.channels)
        if num_channels > 0:
            node.channel_values.append(frame[:num_channels])
            frame = frame[num_channels:]

        for child in node.children:
            frame = self._assign_channel_values(child, frame)

        return frame

    def get_root(self):
        return self.root
