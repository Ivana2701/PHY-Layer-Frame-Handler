import numpy as np

## Initializes the PHY Frame Handler.
## :param sync_word_hex: The Sync Word in hexadecimal format. Default is "2DD4" (10101101 11010100 in binary).
class PHYFrameHandler:
    def __init__(self, sync_word_hex="2DD4"):
 
        # Convert hex sync word to a list of bits [0, 1]
        self.sync_word_bits = self._hex_to_bits(sync_word_hex)
        self.sync_length = len(self.sync_word_bits)
        
        # Bipolar conversion (0 -> -1, 1 -> 1) for better cross-correlation
        self.bipolar_sync = np.where(np.array(self.sync_word_bits) == 0, -1, 1)
        
        # Statistics
        self.stats = {
            "total_detected": 0,
            "valid_crc": 0,
            "corrupted_crc": 0
        }

    def _hex_to_bits(self, hex_string):
        num_bits = len(hex_string) * 4
        val = int(hex_string, 16)
        return [(val >> i) & 1 for i in range(num_bits - 1, -1, -1)]

    def _bits_to_bytes(self, bit_list):
        byte_array = bytearray()
        for i in range(0, len(bit_list), 8):
            byte_chunk = bit_list[i:i+8]
            if len(byte_chunk) == 8:
                val = sum(bit << (7-j) for j, bit in enumerate(byte_chunk))
                byte_array.append(val)
        return byte_array

    # Calculates a standard CRC-16-CCITT (Poly: 0x1021, Init: 0xFFFF).
    def calculate_crc16(self, data: bytearray):
        crc = 0xFFFF
        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc

    # Uses cross-correlation to find the sync word in the bitstream. Returns indices where potential frames start.
    def detect_sync_words(self, bitstream, threshold=0.9):
     
        # Convert bitstream to bipolar (-1, 1)
        bipolar_stream = np.where(np.array(bitstream) == 0, -1, 1)
        
        # Cross-correlate stream with sync word
        correlation = np.correlate(bipolar_stream, self.bipolar_sync, mode='valid')
        
        # Find peaks where correlation exceeds threshold (perfect match = self.sync_length)
        peak_threshold = self.sync_length * threshold
        sync_indices = np.where(correlation >= peak_threshold)[0]
        
        return sync_indices

    ## Scans bitstream, extracts payloads, checks CRC, and logs stats.
    ## Assumes Frame Structure: [Sync Word] [1 Byte Length] [Payload] [2 Bytes CRC16]
    def process_bitstream(self, bitstream):
    
        sync_indices = self.detect_sync_words(bitstream)
        
        print(f"--- Processing Stream ---")
        print(f"Found {len(sync_indices)} potential sync word(s) at indices: {sync_indices}")

        for idx in sync_indices:
            self.stats["total_detected"] += 1
            
            # Start reading after the sync word
            cursor = idx + self.sync_length
            
            # 1. Read Length Byte (8 bits)
            if cursor + 8 > len(bitstream):
                self.stats["corrupted_crc"] += 1
                continue
            length_bits = bitstream[cursor:cursor+8]
            payload_length = self._bits_to_bytes(length_bits)[0]
            cursor += 8
            
            # 2. Read Payload
            payload_bits_len = payload_length * 8
            if cursor + payload_bits_len > len(bitstream):
                self.stats["corrupted_crc"] += 1
                continue
            payload_bits = bitstream[cursor:cursor+payload_bits_len]
            payload_bytes = self._bits_to_bytes(payload_bits)
            cursor += payload_bits_len
            
            # 3. Read CRC (16 bits)
            if cursor + 16 > len(bitstream):
                self.stats["corrupted_crc"] += 1
                continue
            crc_bits = bitstream[cursor:cursor+16]
            received_crc_bytes = self._bits_to_bytes(crc_bits)
            received_crc = (received_crc_bytes[0] << 8) | received_crc_bytes[1]
            
            # 4. Verify CRC
            calculated_crc = self.calculate_crc16(payload_bytes)
            
            if calculated_crc == received_crc:
                self.stats["valid_crc"] += 1
                try:
                    decoded_msg = payload_bytes.decode('utf-8')
                except:
                    decoded_msg = payload_bytes.hex()
                print(f"[VALID] Frame at idx {idx} | Payload: '{decoded_msg}'")
            else:
                self.stats["corrupted_crc"] += 1
                print(f"[CORRUPT] Frame at idx {idx} | Calc CRC: {calculated_crc:04X}, Rx CRC: {received_crc:04X}")

    def print_statistics(self):
        print("\n--- Frame Statistics ---")
        print(f"Total Detected : {self.stats['total_detected']}")
        print(f"Valid Frames   : {self.stats['valid_crc']}")
        print(f"Corrupted      : {self.stats['corrupted_crc']}")
        print("------------------------\n")



## Generates a fake demodulated bitstream with noise and embedded frames for testing purposes.
def generate_test_bitstream():
    handler = PHYFrameHandler("2DD4") # Using 0x2DD4 as sync word
    
    # Create an invalid frame (bad CRC)
    payload_bad = bytearray(b"BadData")
    crc_bad = 0x0000 # Intentionally wrong CRC
    frame_bad = handler.sync_word_bits + \
                handler._hex_to_bits(f"{len(payload_bad):02X}") + \
                [bit for byte in payload_bad for i in range(7, -1, -1) for bit in [(byte >> i) & 1]] + \
                handler._hex_to_bits(f"{crc_bad:04X}")

    # Create a valid frame
    payload_good = bytearray(b"Hello SDR!")
    crc_good = handler.calculate_crc16(payload_good)
    frame_good = handler.sync_word_bits + \
                 handler._hex_to_bits(f"{len(payload_good):02X}") + \
                 [bit for byte in payload_good for i in range(7, -1, -1) for bit in [(byte >> i) & 1]] + \
                 handler._hex_to_bits(f"{crc_good:04X}")

    # Embed in random noise
    np.random.seed(42)
    noise_before = np.random.randint(0, 2, 500).tolist()
    noise_middle = np.random.randint(0, 2, 300).tolist()
    noise_after = np.random.randint(0, 2, 200).tolist()

    return noise_before + frame_bad + noise_middle + frame_good + noise_after


if __name__ == "__main__":
    print("Generating simulated RF bitstream...")
    simulated_rx_stream = generate_test_bitstream()
    
    decoder = PHYFrameHandler(sync_word_hex="2DD4")
    decoder.process_bitstream(simulated_rx_stream)
    decoder.print_statistics()