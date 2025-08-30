import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ViewStyle, TextStyle } from 'react-native';
import { Colors } from '../theme/colors';

type PrimaryButtonProps = {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  disabledStyle?: ViewStyle;
  disabledTextStyle?: TextStyle;
};

export default function PrimaryButton({ title, onPress, disabled, style, textStyle, disabledStyle, disabledTextStyle }: PrimaryButtonProps) {
  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={onPress}
      disabled={disabled}
      style={[styles.button, style, disabled ? [styles.buttonDisabled, disabledStyle] : undefined]}
    >
      <Text style={[styles.text, textStyle, disabled ? disabledTextStyle : undefined]}>{title}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    height: 44,
    borderRadius: 14,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.text,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 14,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  text: {
    color: Colors.text,
    fontWeight: '600',
  },
});


