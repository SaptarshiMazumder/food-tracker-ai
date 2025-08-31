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
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#eee',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  flat: {
    shadowColor: 'transparent',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
});


