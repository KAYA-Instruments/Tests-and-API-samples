# Cyclic Buffers API Sample

This API sample demonstrates the use of the cyclic buffer function `KYFG_StreamCreateAndAlloc`. It enables cyclic image acquisition, where images are continuously captured and stored in a pre-allocated buffer in a looped manner. When the buffer is full, new images overwrite the oldest ones, ensuring efficient memory usage and uninterrupted acquisition.

This approach is ideal for high-speed image capture scenarios where real-time processing or continuous streaming is required.

* KYFGLib_API_Sample.py — single camera acqusition sample
* KYFGLib_API_Sample_mutiple_cameras.py — multiple camera acqusition sample
