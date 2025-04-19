import unittest
from wled_controller import WLEDController

class WLEDControllerTest(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        pass
    
    def test_build_command_url(self):
        """Test building command URLs."""
        # Test with basic command
        url = WLEDController.build_command_url("192.168.0.100", "FX=2&FP=67", 5)
        self.assertEqual(url, "http://192.168.0.100/win&FX=2&FP=67&S2=5")
        
        # Test with different IP
        url = WLEDController.build_command_url("10.0.0.1", "FX=54&FP=57", 10)
        self.assertEqual(url, "http://10.0.0.1/win&FX=54&FP=57&S2=10")
    
    def test_calculate_score_param(self):
        """Test score parameter calculation."""
        # Test with default base and multiplier
        param = WLEDController.calculate_score_param(1.5)
        self.assertEqual(param, 11)  # 2 + int(1.5 * 6) = 2 + 9 = 11
        
        # Test with zero score
        param = WLEDController.calculate_score_param(0)
        self.assertEqual(param, 2)  # 2 + int(0 * 6) = 2
        
        # Test with custom base and multiplier
        param = WLEDController.calculate_score_param(2.0, base=5, multiplier=10)
        self.assertEqual(param, 25)  # 5 + int(2.0 * 10) = 5 + 20 = 25
    
    def test_get_command_for_measure(self):
        """Test retrieving commands for measures."""
        # Define test command settings
        command_settings = {
            0: "FX=2&FP=67",
            4: "FX=54&FP=57",
            8: "FX=19&FP=10"
        }
        
        # Test existing measure
        command = WLEDController.get_command_for_measure(4, command_settings)
        self.assertEqual(command, "FX=54&FP=57")
        
        # Test non-existent measure
        command = WLEDController.get_command_for_measure(2, command_settings)
        self.assertIsNone(command)

if __name__ == '__main__':
    unittest.main()
