"""Test suite for FIESTA-Py package."""

import pytest
import pandas as pd
import numpy as np
from fiesta.dat import filter_data, frequency_table
from fiesta.utils import check_dataframe, check_column_exists


class TestDataFiltering:
    """Tests for data filtering functions."""
    
    def test_filter_simple(self):
        """Test simple filter expression."""
        df = pd.DataFrame({
            'A': [1, 2, 3, 4, 5],
            'B': ['a', 'b', 'c', 'd', 'e']
        })
        
        result = filter_data(df, xfilter="A > 2")
        assert len(result['xf']) == 3
        assert result['xf']['A'].min() == 3
    
    def test_filter_multiple_conditions(self):
        """Test filter with multiple conditions."""
        df = pd.DataFrame({
            'FORTYPCD': [182, 184, 221, 221, 182],
            'STDSZCD': [1, 2, 1, 2, 1]
        })
        
        result = filter_data(df, xfilter="FORTYPCD == 221 and STDSZCD == 1")
        assert len(result['xf']) == 1
    
    def test_filter_empty_result(self):
        """Test filter that returns empty result."""
        df = pd.DataFrame({
            'A': [1, 2, 3]
        })
        
        with pytest.warns(UserWarning):
            result = filter_data(df, xfilter="A > 10")
            assert len(result['xf']) == 0


class TestFrequencyTables:
    """Tests for frequency table functions."""
    
    def test_simple_frequency(self):
        """Test simple frequency table."""
        df = pd.DataFrame({
            'TYPE': ['A', 'B', 'A', 'C', 'B', 'A']
        })
        
        freq = frequency_table(df, 'TYPE')
        assert len(freq) == 3
        assert freq[freq['TYPE'] == 'A']['count'].values[0] == 3
    
    def test_weighted_frequency(self):
        """Test weighted frequency table."""
        df = pd.DataFrame({
            'TYPE': ['A', 'B', 'A'],
            'WEIGHT': [10, 20, 15]
        })
        
        freq = frequency_table(df, 'TYPE', weights='WEIGHT')
        assert freq[freq['TYPE'] == 'A']['weighted_count'].values[0] == 25


class TestUtilities:
    """Tests for utility functions."""
    
    def test_check_dataframe(self):
        """Test DataFrame validation."""
        df = pd.DataFrame({'A': [1, 2, 3]})
        result = check_dataframe(df, "test")
        assert isinstance(result, pd.DataFrame)
        
        with pytest.raises(TypeError):
            check_dataframe([1, 2, 3], "test")
    
    def test_check_column_exists(self):
        """Test column existence check."""
        df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        
        # Should not raise
        check_column_exists(df, ['A', 'B'], "test")
        
        # Should raise
        with pytest.raises(ValueError):
            check_column_exists(df, ['C'], "test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
