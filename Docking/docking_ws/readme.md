# Articubot: From Mapping to AprilTag Docking

Graduation Project: Robot `articubot_one` (ROS 2 **Humble** + Gazebo Classic) for cafe mapping, Nav2 waypoint navigation, and AprilTag camera-based docking.

```
Gazebo (cafe.world + robot + tag)
   │  /scan  /camera/image_raw  /diff_cont/odom
   ├──► slam_toolbox ───────────► cafe_map1.pgm/.yaml        (Stage 1: Mapping)
   ├──► Nav2 (map_server + AMCL + planner + controller)      (Stage 2: Navigation)
   └──► apriltag_ros ─► dock_pose_publisher ─► docking_server (Stage 3: Docking)
                                   │
                  /cmd_vel ─► twist_mux ─► diff_cont ─► Wheels
```

## Table of Contents
1. [One-Time Setup](#1-one-time-setup)
2. [Cleanup Before Execution](#2-cleanup-before-execution)
3. [Stage 1: Mapping (SLAM)](#3-stage-1-mapping-slam)
4. [Stage 2: Navigation Testing](#4-stage-2-navigation-testing)
5. [Stage 3: Docking Testing](#5-stage-3-docking-testing)
6. [Daily Routine (After Map is Ready)](#6-daily-routine-after-map-is-ready)
7. [Key Values and Calculations](#7-key-values-and-calculations)
8. [Common Issues and Solutions](#8-common-issues-and-solutions)
9. [Important Technical Notes](#9-important-technical-notes)
10. [Modified Files](#10-modified-files)
11. [Next Steps](#11-next-steps)

---

## 1. One-Time Setup

### 1.1 Required Packages
```bash
sudo apt update
sudo apt install ros-humble-slam-toolbox ros-humble-nav2-bringup \
                 ros-humble-apriltag-ros ros-humble-image-proc \
                 ros-humble-opennav-docking ros-humble-opennav-docking-msgs \
                 ros-humble-teleop-twist-keyboard
```
(Other packages like `twist_mux`, `gazebo_ros`, and `ros2_control` are included with `articubot_one`.)

### 1.2 Build the Workspace
```bash
cd ~/grad_project/docking_ws
colcon build --symlink-install      # symlink: modify yaml/launch without rebuilding
source install/setup.bash
```
> After modifying C++/CMake files or adding new files (e.g., a new world), run `colcon build` again.

### 1.3 Auto-source Environment (Optional & Convenient)
```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source ~/grad_project/docking_ws/install/setup.bash" >> ~/.bashrc
```
If not configured, execute both commands in **every new terminal**:
```bash
source /opt/ros/humble/setup.bash
source ~/grad_project/docking_ws/install/setup.bash
```

### 1.4 Configuration Directories and Files
```bash
mkdir -p ~/grad_project/docking_ws/maps ~/grad_project/docking_ws/config
```

**`config/nav2_params.yaml`**: Copy default parameters and modify:
```bash
cp /opt/ros/humble/share/nav2_bringup/params/nav2_params.yaml ~/grad_project/docking_ws/config/nav2_params.yaml
# Robot publishes odom on /diff_cont/odom instead of /odom (in bt_navigator and velocity_smoother)
sed -i -E 's#odom_topic: "?/?odom"?#odom_topic: "/diff_cont/odom"#' ~/grad_project/docking_ws/config/nav2_params.yaml
grep -n "odom_topic" ~/grad_project/docking_ws/config/nav2_params.yaml   # Two lines should appear
```
Manually adjust according to the robot specifications:
- `robot_radius` in `local_costmap` and `global_costmap` (default `0.22`).
- In `amcl`: `base_frame_id: "base_link"`, `odom_frame_id: "odom"`, `scan_topic: scan`.

**`config/mapping.rviz`**: RViz configuration file for mapping (Fixed Frame = `map`, `/map` with correct QoS, `/scan`, TF, RobotModel). Provided with the README; place it in `~/grad_project/docking_ws/config/`.

---

## 2. Cleanup Before Execution

A common issue is an old `gzserver` process running in the background, showing the old world. **Run this before every session:**
```bash
pkill -9 gzserver; pkill -9 gzclient; pkill -f rviz2
pkill -f slam_toolbox; pkill -f component_container; pkill -f rqt_image_view
sleep 2; pgrep -a gz        # Should return nothing
```

---

## 3. Stage 1: Mapping (SLAM)

> **Important Rule:** Map origin = robot position when SLAM starts. Always start with the robot unmoved at the spawn location so `dock_database.yaml` and initial pose remain correct.

Execute each command in a **separate terminal**.

**T1: Gazebo (Cafe + Robot + Tag)**
```bash
ros2 launch articubot_docking sim_dock.launch.py
```
Wait ~15 seconds. Verify controllers are active:
```bash
ros2 control list_controllers      # diff_cont and joint_broadcaster must be active
```

**T2: SLAM**
```bash
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=true \
  slam_params_file:=/opt/ros/humble/share/slam_toolbox/config/mapper_params_online_async.yaml
```
`Registering sensor: [Custom Described Lidar]` should appear. (Two laser range warnings can be ignored.)

**T3: Verify `map` frame exists, then launch RViz** (This order prevents `Frame [map] does not exist` errors)
```bash
ros2 run tf2_ros tf2_echo map odom          # Once values print: Ctrl+C
rviz2 -d ~/grad_project/docking_ws/config/mapping.rviz --ros-args -p use_sim_time:=true
```
If `map odom` does not exist yet, move the robot slightly using teleop.

**T4: Teleop** (Note `/cmd_vel_joy` instead of `/cmd_vel`, refer to [Section 9](#9-important-technical-notes))
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/cmd_vel_joy
```
- The teleop terminal must be focused when pressing keys.
- `i` forward, `k` stop, `u`/`o` turn, `z`/`x` decrease/increase speed.

### How to Create a Good Map
- Move **slowly** (lower speed yields a cleaner map).
- Drive around **every** obstacle and follow all four walls.
- Circle around the tag and `dock_panel` to ensure visibility.
- If walls appear doubled or duplicated, movement was too fast; restart mapping.
- Complete when all four walls are closed with no internal black gaps.

### Saving the Map
```bash
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
  "{name: {data: '$HOME/grad_project/docking_ws/maps/cafe_map1'}}"
ls ~/grad_project/docking_ws/maps         # cafe_map1.yaml + cafe_map1.pgm
```
Open `cafe_map1.pgm` to inspect it before proceeding. A `result: 0` response indicates success.

> **Do not use `map_saver_cli`** with `slam_toolbox`: it throws `Failed to spin map subscription` due to QoS. The service is more reliable.

After saving, close everything (Section 2).

---

## 4. Stage 2: Navigation Testing

**T1: Gazebo** (Same command, robot must start at spawn)
```bash
ros2 launch articubot_docking sim_dock.launch.py
```

**T2: Nav2 with Map** (After ~15 seconds)
```bash
ros2 launch nav2_bringup bringup_launch.py \
  use_sim_time:=true \
  map:=$HOME/grad_project/docking_ws/maps/cafe_map1.yaml \
  params_file:=$HOME/grad_project/docking_ws/config/nav2_params.yaml
```
Wait for `Managed nodes are active`. Seeing `AMCL cannot publish a pose... Please set the initial pose` is normal until an initial pose is set.

**T3: Publish Initial Pose numerically** (Robot at spawn = map origin)
```bash
ros2 topic pub --once /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
"{header: {frame_id: 'map'}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}, covariance: [0.05,0,0,0,0,0, 0,0.05,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0.02]}}"
```
If it fails the first time, repeat it after Nav2 becomes active.

**T4: RViz**
```bash
rviz2 -d /opt/ros/humble/share/nav2_bringup/rviz/nav2_default_view.rviz --ros-args -p use_sim_time:=true
```
Uncheck `Image`, `Realsense`, and `Bumper Hit` to reduce resource consumption.

### Success Criteria
1. `Navigation: active` and `Localization: active` in the Navigation 2 panel.
2. Green particle swarm (AMCL particles) clustered around the robot, and lidar lines aligned with walls. If scattered, rotate the robot slightly via teleop.
3. Click **Nav2 Goal** behind a table: the robot navigates around obstacles (`Feedback: reached` and `Goal succeeded` in Nav2 logs).

---

## 5. Stage 3: Docking Testing

### 5.1 Dock Location in `dock_database.yaml`
```bash
cat > ~/grad_project/docking_ws/src/articubot_docking/config/dock_database.yaml <<'EOF'
docks:
  dock0:
    type: 'articubot_dock'
    frame: map
    pose: [2.55, 0.0, 0.0]     # [x, y, yaw] = base_link position when docked
EOF
cd ~/grad_project/docking_ws && colcon build --packages-select articubot_docking && source install/setup.bash
```
(Calculated in [Section 7](#7-key-values-and-calculations).)

### 5.2 Launch Camera and `docking_server`
Nav2 and Gazebo must be running (Stage 2). In a new terminal:
```bash
ros2 launch articubot_docking docking_bringup.launch.py
```
This starts `apriltag_ros` + `dock_pose_publisher` + `docking_server`. Verify:
- `Docking Server has 1 dock types and 1 dock instances available`
- `Managed nodes are active`

### 5.3 Verify Camera Detects the Tag
The robot must **face the tag** (visible up to ~2.5m):
```bash
ros2 topic hz /detected_dock_pose                      # ~10 Hz if detected
ros2 run tf2_ros tf2_echo odom dock_tag                # Transform values if detected
ros2 run rqt_image_view rqt_image_view /camera/image_raw   # Tag centered in image
```

### 5.4 Full Docking Test (with Nav2)
1. Send the robot away from the tag using **Nav2 Goal** to a point in the northern part of the room.
2. Send the goal action:
```bash
ros2 action send_goal /dock_robot opennav_docking_msgs/action/DockRobot \
"{use_dock_id: true, dock_id: 'dock0', navigate_to_staging_pose: true, max_staging_time: 1000.0}" --feedback
```
Or via client script:
```bash
ros2 run articubot_docking dock_client.py dock --dock-id dock0 --navigate
```

**Feedback States:**

| State | Meaning |
|---|---|
| 1 | NAV_TO_STAGING_POSE: Nav2 guides the robot to staging position |
| 2 | INITIAL_PERCEPTION: Waiting for camera to find the tag |
| 3 | CONTROLLING: Precision approach using camera |
| 4 | WAITING_FOR_CHARGE |

Success indicators: `success: true`, `error_code: 0`, and `Goal finished with status: SUCCEEDED`.

### 5.5 Undock
```bash
ros2 action send_goal /undock_robot opennav_docking_msgs/action/UndockRobot \
"{dock_type: 'articubot_dock', max_undocking_time: 30.0}" --feedback
# Or: ros2 run articubot_docking dock_client.py undock
```

### 5.6 Error Codes

| Code | Meaning | Solution |
|---|---|---|
| 901 | `dock0` not in database | Check name and `dock_database.yaml` |
| 902 | Invalid dock | Check `type` and `frame` |
| 903 | Nav2 failed to reach staging pose | Check Nav2 logs; pose might be inside an obstacle |
| 904 | Camera could not find tag | Check `topic hz /detected_dock_pose`, ensure robot faces tag |
| 905 | Control issue | Monitor `/cmd_vel` and `/diff_cont/cmd_vel_unstamped` |
| 906 | Charging failure | In simulation, set `use_battery_status: false` |
| 907 | Timeout | Robot is too slow or stalled |

---

## 6. Daily Routine (After Map is Ready)

Following Section 2 (Cleanup), run each command in a separate terminal:

```bash
# T1: Gazebo
ros2 launch articubot_docking sim_dock.launch.py

# T2: Nav2 (After ~15 seconds)
ros2 launch nav2_bringup bringup_launch.py use_sim_time:=true \
  map:=$HOME/grad_project/docking_ws/maps/cafe_map1.yaml \
  params_file:=$HOME/grad_project/docking_ws/config/nav2_params.yaml

# T3: Initial pose (Once after Nav2 is active)
ros2 topic pub --once /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
"{header: {frame_id: 'map'}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}, covariance: [0.05,0,0,0,0,0, 0,0.05,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0.02]}}"

# T4: RViz
rviz2 -d /opt/ros/humble/share/nav2_bringup/rviz/nav2_default_view.rviz --ros-args -p use_sim_time:=true

# T5: Camera + docking_server
ros2 launch articubot_docking docking_bringup.launch.py

# T6: (Optional) Teleop
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/cmd_vel_joy
```
Then: issue a Nav2 Goal away from the tag, followed by `send_goal /dock_robot ... navigate_to_staging_pose: true`.

---

## 7. Key Values and Calculations

| Parameter | Value | Location |
|---|---|---|
| Room dimensions | 7x6 m (x: -3.5..3.5, y: -3..3) | `worlds/cafe.world` |
| Robot spawn = Map origin | Approx. (0, 0) | `sim_dock.launch.py` |
| Tag position (world) | `x = 3.0`, facing `-x` | `cafe.world` + `models/apriltag_dock/model.sdf` |
| Tag size (black square) | 0.16 m | `config/apriltag_36h11.yaml` |
| Tag center height | 0.30 m | `models/apriltag_dock/model.sdf` |
| Camera | z=0.23, pitch=-0.10 (tilted slightly upward), 640x480, hfov 1.089 | `articubot_one/description/camera.xacro` |
| Lidar | 0.3m to 12m, `/scan` | `description/lidar.xacro` |
| `external_detection_translation_x` | -0.45 (base_link stops 0.45m in front of tag plane) | `config/docking_server.yaml` |
| `staging_x_offset` | -0.75 (staging position behind docked pose) | `config/docking_server.yaml` |

**Calculating pose in `dock_database.yaml`:**
- Docked pose x = Tag position − 0.45 = `3.0 − 0.45 = 2.55`
- Staging pose x = Docked − 0.75 = `1.80` (Robot is ~1.15m from the tag, with clear camera view)
- Yaw = 0 (Facing inward toward the wall, along +x)
- Valid only if **Map origin = World origin**. If spawn location changes, remap and recalculate (World tag position − spawn offset).

---

## 8. Common Issues and Solutions

| Symptom | Cause | Solution |
|---|---|---|
| Gazebo opens with old world / obstacles missing | Old `gzserver` running in background | Section 2 (pkill -9) |
| `Frame [map] does not exist` in RViz | RViz opened before SLAM/AMCL published `map→odom` | Start SLAM or Nav2 + initial pose first, then RViz |
| `AMCL cannot publish a pose... set the initial pose` | Initial pose required | Publish via `ros2 topic pub /initialpose` or **2D Pose Estimate** |
| Navigation `inactive` and Localization `active` | `global_costmap` waiting for `map→odom` | Set initial pose |
| `Failed to spin map subscription` | QoS mismatch with `map_saver_cli` | Use `slam_toolbox/save_map` service |
| Robot does not move via teleop | Teleop publishing to wrong topic | Use `cmd_vel:=/cmd_vel_joy` ([Section 9](#9-important-technical-notes)) |
| Robot moves in RViz but Gazebo stays still | Heavy GUI load | Compare `gz model -m my_bot -p` with `/diff_cont/odom`. If both change, it is a display issue; reduce load |
| Scattered green particles | Incorrect initial pose or robot not at spawn | Set correct initial pose and rotate robot |
| RViz freezes or crashes (`exit code -11`) | Heavy displays or OpenGL issues | Remove `Image` and `Particle Swarm`, or use `LIBGL_ALWAYS_SOFTWARE=1 rviz2 ...` |
| `Message Filter dropping message ... queue is full` | TF missing or RViz missing sim time | Run RViz with `--ros-args -p use_sim_time:=true` after SLAM/Nav2 |
| `tf2_echo map dock_tag` is empty | `dock_tag` publishes only when camera sees tag | Run `dock_bringup.launch.py` while robot faces the tag |
| `Exception sending a multicast message: Network is unreachable` | Gazebo network warning | Harmless warning, ignore |

---

## 9. Important Technical Notes

**`cmd_vel` Pipeline (`twist_mux`):**
```
/cmd_vel_joy      (priority 100)  ◄── teleop_twist_keyboard (Use this)
/cmd_vel_tracker  (priority 20)
/cmd_vel          (priority 10)   ◄── Nav2 (velocity_smoother) + docking_server
        └──► twist_mux ──► /diff_cont/cmd_vel_unstamped ──► diff_cont
```
- Do not send teleop commands directly to `/diff_cont/cmd_vel_unstamped`: `twist_mux` constantly overrides it with zeros, causing conflicts.
- Joystick has highest priority; active teleop commands will override Nav2 and docking.

**`use_sim_time:=true`** must be set on **every** node (SLAM, Nav2, RViz, docking). Running RViz without it causes outdated TF transforms.

**Frames:** `map → odom → base_link`. `map→odom` comes from AMCL (or SLAM during mapping). The `docking_server` operates with `fixed_frame: odom`, and in `dock_database.yaml` the dock uses `map`, which works because `map→odom` is established.

**`dock_tag`:** Published by `apriltag_ros` from camera images (not Gazebo directly), so it appears in TF only when the camera detects the tag. `dock_pose_publisher` converts it to `/detected_dock_pose` facing inward toward the wall. `tag_z_points_into_wall: false` is configured because `apriltag_ros` runs with `z_up: false`.

**Nav2 and `docking_server` interaction:** The `docking_server` calls Nav2's `navigate_to_pose` for staging, then takes control and publishes to `/cmd_vel`. If Nav2 is not running, use `navigate_to_staging_pose: false` and ensure the robot is within ≤ 0.5m of the staging pose.

**In Simulation:** No battery or stall detection (`use_battery_status: false`), so docked status is achieved when close to the goal within `docking_threshold: 0.05` m.

---

## 10. Modified Files

| File | Modification |
|---|---|
| `articubot_docking/worlds/cafe.world` | Cafe world (walls + counter + 3 tables + sofa + bookcase + pillar + tag with backing panel) |
| `articubot_docking/launch/sim_dock.launch.py` | Added argument `world` (default `cafe.world`) |
| `articubot_one/description/camera.xacro` | Camera z=0.23 and pitch=-0.10 (previously 0.181 and +0.18 facing down) |
| `articubot_docking/models/apriltag_dock/model.sdf` | Tag center height 0.30 m (previously 0.17) |
| `articubot_docking/config/dock_database.yaml` | `frame: map`, `pose: [2.55, 0.0, 0.0]` |
| `docking_ws/config/nav2_params.yaml` | `odom_topic: /diff_cont/odom`, adjusted `robot_radius` |
| `docking_ws/config/mapping.rviz` | RViz configuration for mapping |
| `docking_ws/maps/cafe_map1.*` | Saved map files |

**Optional Gazebo Optimization:** `<visualize>false</visualize>` for the camera in `camera.xacro`, and `<physics type="ode"><max_step_size>0.004</max_step_size><real_time_update_rate>250</real_time_update_rate></physics>` at the top of `<world>` in `cafe.world`.

**To revert to the old world:**
```bash
ros2 launch articubot_docking sim_dock.launch.py \
  world:=$HOME/grad_project/docking_ws/install/articubot_docking/share/articubot_docking/worlds/docking.world
```

---

## 11. Next Steps

- [ ] **Repeat docking from different start positions** (North, South, near obstacles) and record success rate.
- [ ] **Test undock** followed by re-docking.
- [ ] Enable `use_collision_detection: true` in the controller after verifying `/local_costmap/costmap_raw` is active.
- [ ] Test **detection failure handling** (cover tag or move robot away) and observe retries (`max_retries: 3`) and error codes.
- [ ] **Real Robot Deployment:**
  - `ros2 launch articubot_docking docking_bringup.launch.py use_sim_time:=false use_rectify:=true`
  - Calibrate camera (`camera_info`) since AprilTag requires accurate intrinsics.
  - Print physical tag at exact dimensions (`size: 0.16` for black square) or update `size` in `apriltag_36h11.yaml`.
  - Enable `use_battery_status: true` or stall detection in `docking_server.yaml`.
  - Remap the physical environment and update `dock_database.yaml` with real coordinates.
- [ ] **Backup:** Initialize git repository excluding build/ install/ log directories:
  ```bash
  cd ~/grad_project/docking_ws
  printf "build/\ninstall/\nlog/\n" > .gitignore
  git init && git add src config maps .gitignore && git commit -m "docking project working in cafe world"
  ```
- [ ] If the world or spawn location is modified: **Create a new map** + recalculate `dock_database.yaml`.