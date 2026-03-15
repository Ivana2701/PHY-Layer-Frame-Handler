# Assignment 4: PHY Layer Frame Handler

## Objective
This project implements Physical Layer frame synchronization, decoding, and error checking for a generic UHF Transceiver using discrete cross-correlation. 

## Frame Structure Implemented
Based on standard sub-GHz transceivers (like the CC1101), the handler expects the following frame sequence:
1. **Preamble:** Handled by RF frontend (Hardware AGC settling).
2. **Sync Word:** `0x2DD4` (16 bits) - Detected via Bipolar Cross-Correlation.
3. **Length Byte:** 1 byte determining payload size.
4. **Payload:** Variable length data.
5. **CRC:** 16-bit CRC-CCITT calculated over the payload.

## Setup Instructions
1. Ensure you have Python 3.8+ installed.
2. It is highly recommended to use a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  
   
   # On Windows: venv\Scripts\activate

3. Install the required dependencies:
    ```bash
    pip install -r requirements.txt

4. To test the frame handler using the built-in simulated bitstream generator, simply run:

    ```bash
    python frame_handler.py