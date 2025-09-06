import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ViewStyle, TextStyle, View } from 'react-native';
import { Colors } from '../theme/colors';

type PrimaryButtonProps = {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  disabledStyle?: ViewStyle;
  disabledTextStyle?: TextStyle;
  leftIcon?: React.ReactNode;
};

export default function PrimaryButton({ title, onPress, disabled, style, textStyle, disabledStyle, disabledTextStyle, leftIcon }: PrimaryButtonProps) {
  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={onPress}
      disabled={disabled}
      style={[styles.button, style, disabled ? [styles.buttonDisabled, disabledStyle] : undefined]}
    >
      <View style={styles.contentRow}>
        {/* Always render icon; let disabled color be controlled by provided icon component */}
        {leftIcon ? <View style={styles.iconWrap}>{leftIcon}</View> : null}
        <Text style={[styles.text, textStyle, disabled ? disabledTextStyle : undefined]}>{title}</Text>
      </View>
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
  contentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconWrap: {
    marginRight: 6,
    transform: [{ translateY: 2 }],
  },
  text: {
    color: Colors.text,
    fontWeight: '600',
  },
});


