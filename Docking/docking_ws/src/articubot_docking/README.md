# articubot_docking

Autonomous docking for `articubot_one` (ROS 2 **Humble**, Gazebo Classic) using an AprilTag and
Nav2's docking server (`opennav_docking`).

```
/camera/image_raw + /camera/camera_info      (articubot_one camera.xacro / v4l2_camera)
        |
  apriltag_ros  ──TF──►  camera_link_optical → dock_tag
        |
  dock_pose_publisher.py ──► /detected_dock_pose  (odom frame, heading into the wall)
        |
  opennav_docking (docking_server) ──► /cmd_vel ─► twist_mux ─► diff_cont
        ▲
  action /dock_robot , /undock_robot  (dock_client.py or ros2 action send_goal)
```

## 1. Install dependencies (Humble)
```bash
sudo apt update
sudo apt install ros-humble-apriltag-ros ros-humble-image-proc ros-humble-opennav-docking \
                 ros-humble-opennav-docking-msgs ros-humble-nav2-lifecycle-manager \
                 ros-humble-teleop-twist-keyboard
# if apt can't find opennav_docking, clone branch `humble` of
# https://github.com/open-navigation/opennav_docking into your workspace src/ and rosdep install
```

## 2. Build
```bash
cd ~/dev_ws            # your workspace, with articubot_one and articubot_docking in src/
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select articubot_docking
source install/setup.bash
```

## 3. Run (3 terminals)
```bash
# T1 – simulation (articubot_one sim + world with the AprilTag 3 m ahead)
ros2 launch articubot_docking sim_dock.launch.py

# T2 – AprilTag detection + dock pose publisher + docking server
ros2 launch articubot_docking docking_bringup.launch.py

# T3 – drive the robot to ~x=1.8 (staging area), facing the tag, then dock
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/cmd_vel_joy
ros2 run articubot_docking dock_client.py dock --dock-id dock0
ros2 run articubot_docking dock_client.py undock
```

## 4. Checks, in this order
```bash
ros2 topic list | grep camera                      # /camera/image_raw  /camera/camera_info
ros2 run rqt_image_view rqt_image_view             # tag visible, NOT mirrored
ros2 topic echo /detections --once                 # apriltag_ros sees id 0
ros2 run tf2_ros tf2_echo camera_link_optical dock_tag
ros2 topic echo /detected_dock_pose                # x≈3.0 y≈0 , yaw≈0 (orientation z≈0, w≈1)
ros2 lifecycle get /docking_server                 # active
ros2 topic info /detected_dock_pose -v             # 1 publisher + docking_server subscribing
```

## 5. Troubleshooting
| Symptom | Fix |
|---|---|
| tag looks mirrored in the image | in `models/apriltag_dock/materials/scripts/apriltag_dock.material` use `tag36_11_00000_flipped.png`, rebuild |
| `/detections` empty | tag too far (stay < 2.5 m), wrong `size`, or `family`; check the image really shows the tag |
| yaw of `/detected_dock_pose` is ~π | your apriltag_ros publishes z out of the tag: launch `dock_pose_publisher` with `tag_z_points_into_wall:=false` |
| "robot too far from staging pose" | drive closer (within 0.5 m of x=1.8) or run with `--navigate` once Nav2 works |
| robot stops 1–2 cm early/late | tune `docking_threshold`, `v_linear_min` |
| robot oscillates | lower `k_phi`/`k_delta`, `v_angular_max` in `config/docking_server.yaml` |

## 6. Real robot
* `ros2 launch articubot_docking docking_bringup.launch.py use_sim_time:=false use_rectify:=true`
* Calibrate the camera (`camera_info_url` for v4l2_camera) – AprilTag pose needs real intrinsics.
* Print the tag at exactly `size` (black square) and fix `size` in `config/apriltag_36h11.yaml`.
* Charging detection: set `use_battery_status: true` (+ battery topic) or stall detection in `docking_server.yaml`.
* Replace `frame: odom` with `map` in `config/dock_database.yaml` and use real map coordinates.
