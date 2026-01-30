'''
Author: LiuSheng
Date: 2025-11-28 15:59:16
LastEditTime: 2025-11-28 17:20:53
Description: 
'''

import numpy as np

def load_mat_from_file(cur_file, steep=0.0375):
    """
    step: 表示 相邻帧数据 步长
    """
    import h5py
    with h5py.File(cur_file, 'r') as f:
        pixels_array = f['d']['data'][:]
        pos = f['d']['pos'][:] * steep
        ypos = f['d']['ypos'][:] * steep
        posend = f['d']['posend'][:] * steep
        yposend = f['d']['yposend'][:] * steep
        
        pos_array = np.vstack((pos, ypos, posend, yposend)).T
    return pos_array, pixels_array

def shift_data(raw_pixels, offset_pixel):
    print(raw_pixels.shape, offset_pixel)
    # offset_pixel = cfg.efficiency_cfg.shift_pixel
    
    if raw_pixels.ndim == 4:
        # # raw_pixels shape: DataNum * FrameNum * PixelNum * BinNum
        # DataNum, FrameNum, PixelNum, BinNum = raw_pixels.shape
        # shifted_pixels = np.zeros_like(raw_pixels)
        # for i in range(PixelNum):
        #     offset = offset_pixel*(i % 4)
        #     shifted_pixels[:, :, i, :] = np.roll(raw_pixels[:, :, i, :], offset, axis=1)
            # raw_pixels: (DataNum, FrameNum, PixelNum, BinNum)
        D, F, P, B = raw_pixels.shape

        # Per-pixel offset，必须转 int（roll 不支持 float）
        offsets = ((np.arange(P) % 4) * offset_pixel).astype(int)  # shape=(P,)

        # 构造 axis=1 的索引，FrameNum 方向
        base = np.arange(F)[:, None]            # shape (F,1)
        idx = (base - offsets[None, :]) % F      # shape (F,P)

        # 一次性完成所有 pixel 的 roll（DataNum, FrameNum, PixelNum, BinNum）
        shifted_pixels = raw_pixels[:, idx, np.arange(P)[None, :], :]
        
        for idx, (raw, shifted) in enumerate(zip(raw_pixels, shifted_pixels)):
            if cfg.debug_dir is not None:
                shift_plot_item(idx, raw[:, :, -1:], shifted[:, :, -1:], cfg.debug_dir)
            
        return shifted_pixels

    elif raw_pixels.ndim == 3:
        # raw_pixels shape: FrameNum * PixelNum * BinNum
        FrameNum, PixelNum, BinNum = raw_pixels.shape
        
        # shifted_pixels = np.zeros_like(raw_pixels)
        # for i in range(PixelNum):
        #     offset = offset_pixel*(i % 4)
        #     shifted_pixels[:, i, :] = np.roll(raw_pixels[:, i, :], offset, axis=0)
        
        # Per-pixel offset (integer)
        offsets = ((np.arange(PixelNum) % 4) * offset_pixel).astype(int)
        # Base index for axis=0: [0 ... FrameNum-1]
        base = np.arange(FrameNum)[:, None]  # shape = (FrameNum,1)
        # (FrameNum, PixelNum) 的重排索引
        # new_idx[f, i] = (f - offsets[i]) % FrameNum
        new_idx = (base - offsets) % FrameNum
        # 使用高级索引完成整体重排
        shifted_pixels = raw_pixels[new_idx, np.arange(PixelNum)[None, :], :]
        
        return shifted_pixels
    
    elif raw_pixels.ndim == 2:
        # raw_pixels shape: FrameNum * PixelNum
        FrameNum, PixelNum = raw_pixels.shape
        
        # Per-pixel offset (integer)
        offsets = ((np.arange(PixelNum) % 4) * offset_pixel).astype(int)
        # Base index for axis=0: [0 ... FrameNum-1]
        base = np.arange(FrameNum)[:, None]  # shape = (FrameNum,1)
        # new_idx[f, i] = (f - offsets[i]) % FrameNum
        new_idx = (base - offsets) % FrameNum
        # 使用高级索引完成整体重排
        shifted_pixels = raw_pixels[new_idx, np.arange(PixelNum)[None, :]]
        
        return shifted_pixels
    else:
        raise ValueError(f"raw_pixels ndim must be 3 or 4, but got {raw_pixels.ndim}")