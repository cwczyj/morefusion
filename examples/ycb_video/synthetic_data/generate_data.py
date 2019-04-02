#!/usr/bin/env python

import datetime
import pathlib

import chainer
import numpy as np
import pybullet
import trimesh

import objslampp

import contrib


def generate_a_video(out, random_state):
    out.mkdir(parents=True, exist_ok=True)

    generator = contrib.simulation.BinTypeSceneGeneration(
        models=objslampp.datasets.YCBVideoModels(),
        n_object=random_state.randint(5, 10),
        random_state=random_state,
    )
    pybullet.resetDebugVisualizerCamera(
        cameraDistance=0.8,
        cameraYaw=45,
        cameraPitch=-60,
        cameraTargetPosition=(0, 0, 0),
    )
    generator.generate()

    Ts_cam2world = generator.random_camera_trajectory()
    camera = trimesh.scene.Camera(resolution=(640, 480), fov=(60, 45))

    for index, T_cam2world in enumerate(Ts_cam2world):
        rgb, depth, instance_label, class_label = generator.render(
            T_cam2world,
            fovy=camera.fov[1],
            height=camera.resolution[1],
            width=camera.resolution[0],
        )
        instance_ids = np.unique(instance_label)
        instance_ids = instance_ids[instance_ids >= 0]
        class_ids = generator.unique_ids_to_class_ids(instance_ids)
        Ts_cad2world = generator.unique_ids_to_poses(instance_ids)
        T_world2cam = np.linalg.inv(T_cam2world)
        Ts_cad2cam = T_world2cam @ Ts_cad2world

        # validation
        n_instance = len(instance_ids)
        assert len(Ts_cad2cam) == n_instance
        assert len(class_ids) == n_instance

        width, height = camera.resolution
        assert rgb.shape == (height, width, 3)
        assert rgb.dtype == np.uint8
        assert depth.shape == (height, width)
        assert depth.dtype == np.float32
        assert instance_label.shape == (height, width)
        assert instance_label.dtype == np.int32
        assert class_label.shape == (height, width)
        assert class_label.dtype == np.int32

        assert Ts_cad2cam.shape == (n_instance, 4, 4)
        assert Ts_cad2cam.dtype == np.float64
        assert T_cam2world.shape == (4, 4)
        assert T_cam2world.dtype == np.float64

        data = dict(
            rgb=rgb,
            depth=depth,
            instance_label=instance_label,
            class_label=class_label,
            instrinsic_matrix=camera.K,
            T_cam2world=T_cam2world,
            Ts_cad2cam=Ts_cad2cam,
            instance_ids=instance_ids,
            class_ids=class_ids,
        )

        npz_file = out / f'{index:08d}.npz'
        print(f'==> Saved: {npz_file}')
        np.savez_compressed(npz_file, **data)

    objslampp.extra.pybullet.del_world()


def main():
    now = datetime.datetime.utcnow()
    timestamp = now.strftime('%Y%m%d_%H%M%S.%f')
    root_dir = chainer.dataset.get_dataset_directory(
        f'wkentaro/objslampp/ycb_video/synthetic_data/{timestamp}'
    )
    root_dir = pathlib.Path(root_dir)

    n_video = 100
    for index in range(1, n_video + 1):
        video_dir = root_dir / f'{index:04d}'
        random_state = np.random.RandomState(index)
        generate_a_video(video_dir, random_state)


if __name__ == '__main__':
    main()
