import React, { PropsWithChildren } from 'react';
import { View, StyleSheet, ViewStyle, StyleProp } from 'react-native';

type CardProps = PropsWithChildren<{
  style?: StyleProp<ViewStyle>;
  flat?: boolean;
}>;

export default function Card({ children, style, flat }: CardProps) {
  return <View style={[styles.card, flat && styles.flat, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 10,
    marginBottom: 12,
    // no borders or shadows
    borderWidth: 0,
    borderColor: 'transparent',
    shadowColor: 'transparent',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
  flat: {
    shadowColor: 'transparent',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
});


