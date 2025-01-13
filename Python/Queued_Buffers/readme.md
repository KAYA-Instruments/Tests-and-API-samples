# Queued Buffers API Sample

This API sample demonstrates the use of queued buffer management for image acquisition. In this mode, buffers are queued in advance, and each captured image is stored in the next available buffer in the queue. Once a buffer is filled, it is processed and then re-queued for subsequent acquisitions.

Queued buffer acquisition provides precise control over buffer handling, making it suitable for scenarios requiring sequential image processing and minimal data loss.

* KYFGLib_Example_QueuedBuffers.py — single camera usage
* KYFGLib_Example_QueuedBuffers_mutiple_cameras.py — multiple camera usage
